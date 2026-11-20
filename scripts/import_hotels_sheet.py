"""Reviewed, additive one-time import of sheet customer locations.

Run against a selected engine using import_hotels(). No Google credentials, no
updates to addresses/names, no deletion, no devices or maintenance visits created.
"""
import re
import uuid
from sqlalchemy import select
from app.models import Hotel

NON_HOTEL_TABS = {'GRAHA PENA LT3','GRAHA PENA LT5','GRAHA PENA LT9','GRAHA PENA LT19',
                  'PGFC','RS ORTHOPEDI','SES','SMAN 1 WONOAYU','SDIT NURUL'}


def normalized(value):
    return re.sub(r'[^\w]+','',str(value or '').casefold())


def plan_import(session, manifest, scope, reviewed_matches=None):
    if scope not in ('all','hotels'):raise ValueError('Scope must be explicitly selected')
    rows=manifest['rows']; spreadsheet=manifest['spreadsheet_id']
    existing=list(session.scalars(select(Hotel)));by_id={str(h.id):h for h in existing}
    by_name={}
    for hotel in existing:by_name.setdefault(normalized(hotel.name),[]).append(hotel)
    actions=[];seen=set();claimed=set()
    for row in rows:
        tab=row['source_sheet']
        if scope=='hotels' and tab in NON_HOTEL_TABS:continue
        if tab in seen:raise ValueError('Repeated source sheet')
        seen.add(tab)
        if not all(isinstance(row.get(k),str) and row[k].strip() for k in ('name','address','customer_name')):
            raise ValueError('Incomplete source location: '+tab)
        if len(row['name'])>200 or len(row['customer_name'])>200:raise ValueError('Name too long')
        identifier=uuid.uuid5(uuid.NAMESPACE_URL,'google-sheets:'+spreadsheet+':'+tab)
        mapped=(reviewed_matches or {}).get(tab)
        if mapped:
            hotel=by_id.get(mapped['id'])
            if not hotel or hotel.name!=mapped['expected_name']:raise ValueError('Reviewed match changed: '+tab)
        else:
            matches=by_name.get(normalized(row['name']),[])
            if len(matches)>1:raise ValueError('Ambiguous existing location: '+tab)
            hotel=by_id.get(str(identifier)) or (matches[0] if matches else None)
        target_id=str(hotel.id) if hotel else str(identifier)
        if target_id in claimed:raise ValueError('Multiple sheets mapped to one location')
        claimed.add(target_id)
        fill={k:row[k] for k in ('address','customer_name') if hotel and not (getattr(hotel,k) or '').strip()}
        actions.append({'source_sheet':tab,'id':target_id,'action':'create' if not hotel else 'fill_missing' if fill else 'keep',
            'name':row['name'],'address':row['address'],'customer_name':row['customer_name'],'fill':fill})
    return actions


def import_hotels(session,manifest,scope,reviewed_matches=None,apply=False):
    # Caller owns the transaction. Serialize imports against existing master rows.
    if apply:session.execute(select(Hotel.id).order_by(Hotel.id).with_for_update()).all()
    actions=plan_import(session,manifest,scope,reviewed_matches)
    if apply:
        for action in actions:
            if action['action']=='create':
                session.add(Hotel(id=uuid.UUID(action['id']),name=action['name'],address=action['address'],customer_name=action['customer_name']))
            elif action['action']=='fill_missing':
                hotel=session.get(Hotel,uuid.UUID(action['id']))
                for key,value in action['fill'].items():setattr(hotel,key,value)
        session.flush()
    return actions
