import secrets
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app import models as m, schemas as s
from app.security import hash_password, verify_password, token_hash

router = APIRouter()
bearer = HTTPBearer(auto_error=False)
# Equal-cost password verification for unknown usernames.
_login_attempts = OrderedDict()
_login_lock = threading.Lock()


def throttle_login(request: Request):
    # Per-process source-IP limit; do not trust forwarded headers.
    key = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    with _login_lock:
        attempts = [t for t in _login_attempts.pop(key, []) if now - t < 60]
        if len(attempts) >= 20:
            _login_attempts[key] = attempts
            raise HTTPException(429, 'Too many login attempts', headers={'Retry-After': '60'})
        attempts.append(now)
        _login_attempts[key] = attempts
        if len(_login_attempts) > 4096:
            _login_attempts.popitem(last=False)


_dummy_hash = hash_password(secrets.token_urlsafe(32))


def db(request: Request):
    with Session(request.app.state.engine) as session:
        yield session


def save(session):
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, 'Conflicting data or referenced record')


def current(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), session: Session = Depends(db)):
    error = HTTPException(401, 'Invalid or expired credentials', headers={'WWW-Authenticate': 'Bearer'})
    if not credentials:
        raise error
    login = session.get(m.LoginSession, token_hash(credentials.credentials))
    if not login or login.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        raise error
    user = session.get(m.User, login.user_id)
    if not user or not user.active:
        raise error
    return user


def supervisor(user=Depends(current)):
    if user.role != 'supervisor':
        raise HTTPException(403, 'Supervisor required')
    return user


def get(session, model, identifier):
    obj = session.get(model, identifier)
    if obj is None:
        raise HTTPException(404, 'Record not found')
    return obj


@router.post('/auth/login')
def login(data: s.Login, response: Response, session: Session = Depends(db), limited=Depends(throttle_login)):
    user = session.scalar(select(m.User).where(m.User.username == data.username))
    valid = verify_password(data.password, user.password_hash if user else _dummy_hash)
    if not valid or not user or not user.active:
        raise HTTPException(401, 'Invalid credentials', headers={'WWW-Authenticate': 'Bearer'})
    token = secrets.token_urlsafe(32)
    session.add(m.LoginSession(token_hash=token_hash(token), user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=8)))
    save(session)
    response.headers['Cache-Control'] = 'no-store'
    return {'access_token': token, 'token_type': 'bearer', 'expires_in': 28800}


@router.post('/auth/logout', status_code=204)
def logout(credentials=Depends(bearer), user=Depends(current), session: Session = Depends(db)):
    session.execute(delete(m.LoginSession).where(m.LoginSession.token_hash == token_hash(credentials.credentials)))
    save(session)


@router.get('/auth/me', response_model=s.UserOutput)
def me(user=Depends(current)):
    return user


def validate_relations(session, model, values):
    if model is m.Device:
        get(session, m.Hotel, values['hotel_id'])
    if model is m.Schedule:
        get(session, m.Device, values['device_id'])
        tech = get(session, m.User, values['technician_id'])
        if not tech.active or tech.role != 'technician':
            raise HTTPException(422, 'Assignee must be an active technician')


def register(path, model, create_schema, update_schema, output_schema):
    def listing(offset: int = 0, limit: int = 50, user=Depends(current), session: Session = Depends(db)):
        if offset < 0 or not 1 <= limit <= 100:
            raise HTTPException(422, 'Invalid pagination')
        query = select(model).order_by(model.id)
        if model is m.User and user.role != 'supervisor':
            raise HTTPException(403, 'Supervisor required')
        if model is m.Schedule and user.role == 'technician':
            query = query.where(m.Schedule.technician_id == user.id)
        return session.scalars(query.offset(offset).limit(limit)).all()

    def read(identifier: UUID, user=Depends(current), session: Session = Depends(db)):
        obj = get(session, model, identifier)
        if model is m.User and user.role != 'supervisor':
            raise HTTPException(403, 'Supervisor required')
        if model is m.Schedule and user.role == 'technician' and obj.technician_id != user.id:
            raise HTTPException(404, 'Record not found')
        return obj

    def create(data: create_schema, user=Depends(supervisor), session: Session = Depends(db)):
        values = data.model_dump()
        if model is m.User:
            values['password_hash'] = hash_password(values.pop('password'))
        validate_relations(session, model, values)
        obj = model(**values)
        session.add(obj)
        save(session)
        session.refresh(obj)
        return obj

    def update(identifier: UUID, data: update_schema, user=Depends(supervisor), session: Session = Depends(db)):
        obj = get(session, model, identifier)
        values = data.model_dump()
        if model is m.Schedule:
            # Lock the schedule to serialize assignment changes with visit creation.
            obj = session.scalar(select(m.Schedule).where(m.Schedule.id == identifier).with_for_update())
            if session.scalar(select(m.Visit.id).where(m.Visit.schedule_id == identifier)):
                raise HTTPException(409, 'Schedule with a visit cannot be replaced')
        if model is m.User:
            if obj.id == user.id and (not values['active'] or values['role'] != 'supervisor'):
                raise HTTPException(409, 'Cannot disable or demote yourself')
            password = values.pop('password')
            if password:
                values['password_hash'] = hash_password(password)
            session.execute(delete(m.LoginSession).where(m.LoginSession.user_id == obj.id))
        validate_relations(session, model, values)
        for key, value in values.items():
            setattr(obj, key, value)
        save(session)
        session.refresh(obj)
        return obj

    def remove(identifier: UUID, user=Depends(supervisor), session: Session = Depends(db)):
        obj = get(session, model, identifier)
        if model is m.User and obj.id == user.id:
            raise HTTPException(409, 'Cannot delete yourself')
        session.delete(obj)
        save(session)

    router.add_api_route(path, listing, methods=['GET'], response_model=list[output_schema])
    router.add_api_route(path + '/{identifier}', read, methods=['GET'], response_model=output_schema)
    router.add_api_route(path, create, methods=['POST'], response_model=output_schema, status_code=201)
    router.add_api_route(path + '/{identifier}', update, methods=['PUT'], response_model=output_schema)
    router.add_api_route(path + '/{identifier}', remove, methods=['DELETE'], status_code=204)


register('/hotels', m.Hotel, s.HotelInput, s.HotelInput, s.HotelOutput)
register('/devices', m.Device, s.DeviceInput, s.DeviceInput, s.DeviceOutput)
register('/users', m.User, s.UserCreate, s.UserUpdate, s.UserOutput)
register('/schedules', m.Schedule, s.ScheduleInput, s.ScheduleInput, s.ScheduleOutput)


@router.patch('/schedules/{identifier}/progress', response_model=s.ScheduleOutput)
def progress(identifier: UUID, data: s.Progress, user=Depends(current), session: Session = Depends(db)):
    obj = session.scalar(select(m.Schedule).where(m.Schedule.id == identifier).with_for_update())
    if obj is None:
        raise HTTPException(404, 'Record not found')
    if user.role == 'technician' and obj.technician_id != user.id:
        raise HTTPException(404, 'Record not found')
    if session.scalar(select(m.Visit.id).where(m.Visit.schedule_id == identifier)):
        raise HTTPException(409, 'Visit workflow must determine schedule completion')
    obj.status, obj.notes = data.status, data.notes
    save(session)
    session.refresh(obj)
    return obj


@router.post('/visits', response_model=s.VisitOutput, status_code=201)
def create_visit(data: s.VisitCreate, user=Depends(supervisor), session: Session = Depends(db)):
    schedule = session.scalar(select(m.Schedule).where(m.Schedule.id == data.schedule_id).with_for_update())
    if schedule is None:
        raise HTTPException(404, 'Record not found')
    tech = get(session, m.User, schedule.technician_id)
    if schedule.status != 'pending' or not tech.active or tech.role != 'technician':
        raise HTTPException(409, 'Visit requires a pending schedule and active technician')
    if data.template_id is not None:
        template = get(session, m.ChecklistTemplate, data.template_id)
        device = get(session, m.Device, schedule.device_id)
        if template.device_type != device.device_type:
            raise HTTPException(422, 'Template must match device type')
    visit = m.Visit(schedule_id=schedule.id, technician_id=schedule.technician_id, template_id=data.template_id)
    session.add(visit)
    save(session)
    session.refresh(visit)
    return visit


def visible_visit(session, identifier, user):
    visit = get(session, m.Visit, identifier)
    if user.role == 'technician' and visit.technician_id != user.id:
        raise HTTPException(404, 'Record not found')
    return visit


@router.get('/visits', response_model=list[s.VisitOutput])
def list_visits(offset: int = 0, limit: int = 50, user=Depends(current), session: Session = Depends(db)):
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, 'Invalid pagination')
    query = select(m.Visit).order_by(m.Visit.id)
    if user.role == 'technician':
        query = query.where(m.Visit.technician_id == user.id)
    return session.scalars(query.offset(offset).limit(limit)).all()


@router.get('/visits/{identifier}', response_model=s.VisitOutput)
def read_visit(identifier: UUID, user=Depends(current), session: Session = Depends(db)):
    return visible_visit(session, identifier, user)


@router.post('/visits/{identifier}/check-in', response_model=s.VisitOutput)
def check_in(identifier: UUID, data: s.CheckIn, user=Depends(current), session: Session = Depends(db)):
    visit = visible_visit(session, identifier, user)
    if user.role != 'technician' or visit.technician_id != user.id:
        raise HTTPException(403, 'Assigned technician required')
    # Atomic comparison prevents two requests from overwriting the first check-in.
    result = session.execute(update(m.Visit).where(
        m.Visit.id == identifier, m.Visit.version == data.expected_version,
        m.Visit.status == 'assigned', m.Visit.technician_id == user.id,
    ).values(**data.model_dump(exclude={'expected_version'}),
             status='in_progress', version=m.Visit.version + 1,
             checked_in_at=datetime.now(timezone.utc)), execution_options={'synchronize_session': False})
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(409, 'Visit changed; reload before retrying')
    save(session)
    session.refresh(visit)
    return visit



def template_output(session, template):
    return {'id': template.id, 'name': template.name, 'device_type': template.device_type,
            'items': session.scalars(select(m.ChecklistItem).where(
                m.ChecklistItem.template_id == template.id).order_by(m.ChecklistItem.position)).all()}


@router.post('/checklist-templates', response_model=s.TemplateOutput, status_code=201)
def create_template(data: s.TemplateCreate, user=Depends(supervisor), session: Session = Depends(db)):
    template = m.ChecklistTemplate(name=data.name, device_type=data.device_type)
    session.add(template)
    session.flush()
    for position, item in enumerate(data.items):
        session.add(m.ChecklistItem(template_id=template.id, position=position, **item.model_dump()))
    save(session)
    return template_output(session, template)


@router.get('/checklist-templates', response_model=list[s.TemplateOutput])
def list_templates(offset: int = 0, limit: int = 50, user=Depends(current), session: Session = Depends(db)):
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, 'Invalid pagination')
    templates = session.scalars(select(m.ChecklistTemplate).order_by(m.ChecklistTemplate.id).offset(offset).limit(limit)).all()
    return [template_output(session, template) for template in templates]


@router.get('/checklist-templates/{identifier}', response_model=s.TemplateOutput)
def read_template(identifier: UUID, user=Depends(current), session: Session = Depends(db)):
    return template_output(session, get(session, m.ChecklistTemplate, identifier))


@router.get('/visits/{identifier}/checklist')
def read_checklist(identifier: UUID, user=Depends(current), session: Session = Depends(db)):
    visit = visible_visit(session, identifier, user)
    results = session.scalars(select(m.ChecklistResult).where(m.ChecklistResult.visit_id == visit.id)).all()
    return {'version': visit.version,
            'template': s.TemplateOutput.model_validate(template_output(session, get(session, m.ChecklistTemplate, visit.template_id))) if visit.template_id else None,
            'answers': [{'item_id': result.item_id, 'answer': result.answer, 'notes': result.notes}
                        for result in results]}


def advance_visit(session, identifier, user, version, allowed_statuses=('in_progress',), **values):
    visit = visible_visit(session, identifier, user)
    if user.role != 'technician' or visit.technician_id != user.id:
        raise HTTPException(403, 'Assigned technician required')
    # Obtain the row write lock before inspecting or changing answers; all visit
    # mutations compare the same version, including check-out.
    result = session.execute(update(m.Visit).where(
        m.Visit.id == identifier, m.Visit.version == version,
        m.Visit.status.in_(allowed_statuses), m.Visit.technician_id == user.id,
    ).values(version=m.Visit.version + 1, **values), execution_options={'synchronize_session': False})
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(409, 'Visit changed; reload before retrying')
    return visit


@router.put('/visits/{identifier}/checklist', response_model=s.VisitOutput)
def save_checklist(identifier: UUID, data: s.ChecklistSave, user=Depends(current), session: Session = Depends(db)):
    visit = advance_visit(session, identifier, user, data.expected_version,
                          allowed_statuses=('in_progress', 'revision_requested'))
    if not visit.template_id:
        raise HTTPException(409, 'Visit has no checklist template')
    item_ids = set(session.scalars(select(m.ChecklistItem.id).where(m.ChecklistItem.template_id == visit.template_id)))
    if any(answer.item_id not in item_ids for answer in data.answers):
        raise HTTPException(422, 'Item is not part of visit template')
    for answer in data.answers:
        result = session.scalar(select(m.ChecklistResult).where(
            m.ChecklistResult.visit_id == identifier, m.ChecklistResult.item_id == answer.item_id))
        if result is None:
            result = m.ChecklistResult(visit_id=identifier, **answer.model_dump())
            session.add(result)
        else:
            result.answer, result.notes = answer.answer, answer.notes
    save(session)
    session.refresh(visit)
    return visit


@router.post('/visits/{identifier}/check-out', response_model=s.VisitOutput)
def check_out(identifier: UUID, data: s.CheckOut, user=Depends(current), session: Session = Depends(db)):
    gps = data.model_dump(exclude={'expected_version', 'pic_exception_reason'})
    values = {'checkout_' + key: value for key, value in gps.items()}
    visit = advance_visit(session, identifier, user, data.expected_version,
                          status='submitted', checked_out_at=datetime.now(timezone.utc),
                          pic_exception_reason=data.pic_exception_reason, **values)
    validate_complete_checklist(session, visit)
    record_visit_event(session, visit, user, 'submitted')
    save(session)
    session.refresh(visit)
    return visit


@router.put('/visits/{identifier}/template', response_model=s.VisitOutput)
def bind_template(identifier: UUID, data: s.VisitTemplate, user=Depends(supervisor), session: Session = Depends(db)):
    visit = get(session, m.Visit, identifier)
    template = get(session, m.ChecklistTemplate, data.template_id)
    schedule = get(session, m.Schedule, visit.schedule_id)
    if template.device_type != get(session, m.Device, schedule.device_id).device_type:
        raise HTTPException(422, 'Template must match device type')
    result = session.execute(update(m.Visit).where(
        m.Visit.id == identifier, m.Visit.version == data.expected_version,
        m.Visit.template_id.is_(None), m.Visit.status.in_(['assigned', 'in_progress']),
    ).values(template_id=template.id, version=m.Visit.version + 1), execution_options={'synchronize_session': False})
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(409, 'Template already bound or visit changed')
    save(session)
    session.refresh(visit)
    return visit



def validate_complete_checklist(session, visit):
    if not visit.template_id:
        raise HTTPException(409, 'Visit has no checklist template')
    required = set(session.scalars(select(m.ChecklistItem.id).where(
        m.ChecklistItem.template_id == visit.template_id, m.ChecklistItem.required.is_(True))))
    answered = set(session.scalars(select(m.ChecklistResult.item_id).where(m.ChecklistResult.visit_id == visit.id)))
    if not required.issubset(answered):
        raise HTTPException(409, 'Required checklist items are incomplete')


def record_visit_event(session, visit, user, action, reason=None):
    # Refresh after the atomic update, then capture immutable JSON rather than
    # references to mutable answer rows. This transaction also commits the event.
    session.refresh(visit)
    answers = session.scalars(select(m.ChecklistResult).where(
        m.ChecklistResult.visit_id == visit.id).order_by(m.ChecklistResult.item_id)).all()
    schedule = get(session, m.Schedule, visit.schedule_id)
    device = get(session, m.Device, schedule.device_id)
    hotel = get(session, m.Hotel, device.hotel_id)
    snapshot = {'visit': s.VisitOutput.model_validate(visit),
                'template': s.TemplateOutput.model_validate(template_output(
                    session, get(session, m.ChecklistTemplate, visit.template_id))),
                'answers': [{'item_id': a.item_id, 'answer': a.answer, 'notes': a.notes} for a in answers],
                'schedule': s.ScheduleOutput.model_validate(schedule, from_attributes=True),
                'device': s.DeviceOutput.model_validate(device, from_attributes=True),
                'hotel': s.HotelOutput.model_validate(hotel, from_attributes=True)}
    session.add(m.VisitEvent(visit_id=visit.id, actor_id=user.id, version=visit.version,
                            action=action, reason=reason, snapshot=jsonable_encoder(snapshot)))


@router.post('/visits/{identifier}/resubmit', response_model=s.VisitOutput)
def resubmit_visit(identifier: UUID, data: s.VisitVersion, user=Depends(current), session: Session = Depends(db)):
    visit = advance_visit(session, identifier, user, data.expected_version,
                          allowed_statuses=('revision_requested',), status='submitted')
    validate_complete_checklist(session, visit)
    # Preserve original physical check-out evidence: this is a report revision.
    record_visit_event(session, visit, user, 'resubmitted')
    save(session)
    session.refresh(visit)
    return visit


@router.post('/visits/{identifier}/review', response_model=s.VisitOutput)
def review_visit(identifier: UUID, data: s.VisitReview, user=Depends(supervisor), session: Session = Depends(db)):
    visit = get(session, m.Visit, identifier)
    # Lock schedule first, matching existing schedule/visit creation operations.
    schedule = session.scalar(select(m.Schedule).where(m.Schedule.id == visit.schedule_id).with_for_update())
    if schedule.status != 'pending':
        raise HTTPException(409, 'Review requires a pending schedule')
    result = session.execute(update(m.Visit).where(
        m.Visit.id == identifier, m.Visit.version == data.expected_version,
        m.Visit.status == 'submitted',
    ).values(status=data.decision, version=m.Visit.version + 1),
        execution_options={'synchronize_session': False})
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(409, 'Visit changed; reload before retrying')
    validate_complete_checklist(session, visit)
    if data.decision == 'approved':
        schedule.status = 'completed'
    record_visit_event(session, visit, user, data.decision, data.reason)
    save(session)
    session.refresh(visit)
    return visit


@router.get('/visits/{identifier}/history', response_model=list[s.VisitEventOutput])
def visit_history(identifier: UUID, offset: int = 0, limit: int = 50,
                  user=Depends(current), session: Session = Depends(db)):
    visible_visit(session, identifier, user)
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, 'Invalid pagination')
    return session.scalars(select(m.VisitEvent).where(m.VisitEvent.visit_id == identifier)
                           .order_by(m.VisitEvent.version).offset(offset).limit(limit)).all()
