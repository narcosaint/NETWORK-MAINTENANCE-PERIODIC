from copy import deepcopy
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models as m
from test_modules import client, isolated_lifespan, login


def test_self_profile_roundtrip_validation_scope_and_conflict(client):
    api,engine=client
    admin=login(api)
    assert api.get('/auth/me/profile').status_code==401
    payload={'username':'profile_tech','name':'Profile QA','role':'technician','password':'strong-secret-456'}
    created=api.post('/users',headers=admin,json=payload)
    assert created.status_code==201,created.text
    tech=login(api,payload['username'],payload['password'])
    empty=api.get('/auth/me/profile',headers=tech)
    assert empty.json()=={'phone':None,'email':None,'division':None,'work_area':None,'version':0}
    assert empty.headers['cache-control']=='private, no-store'
    values={'phone':'+62 812-3456-7890','email':' engineer@example.test ','division':' Network Operations ','work_area':' Bali ','expected_version':0}
    response=api.put('/auth/me/profile',headers=tech,json=values)
    assert response.status_code==200,response.text
    assert response.json()=={'phone':'+6281234567890','email':'engineer@example.test','division':'Network Operations','work_area':'Bali','version':1}
    assert api.get('/auth/me/profile',headers=admin).json()['version']==0
    assert api.put('/auth/me/profile',headers=tech,json=values).status_code==409
    assert api.put('/auth/me/profile',headers=tech,json={**values,'expected_version':1,'role':'supervisor'}).status_code==422
    assert api.put('/auth/me/profile',headers=tech,json={**values,'expected_version':1,'user_id':created.json()['id']}).status_code==422
    for key,bad in [('phone','call-me'),('phone','123'),('email','broken-address'),('email','x@y\n.example'),('division','x'*201)]:
        assert api.put('/auth/me/profile',headers=tech,json={**values,'expected_version':1,key:bad}).status_code==422
    assert api.get('/auth/me',headers=tech).json()['role']=='technician'
    assert api.get('/users',headers=tech).status_code==403
    # Updating contact details does not revoke the current login or alter credentials.
    with Session(engine) as session:
        user=session.scalar(select(m.User).where(m.User.username==payload['username']))
        assert user.active and user.name==payload['name']
        assert user.contact_profile['version']==1
        stored_hash=user.password_hash
    clear=api.put('/auth/me/profile',headers=tech,json={'expected_version':1,'phone':' ','email':None,'division':'','work_area':None})
    assert clear.status_code==200 and clear.json()['phone'] is None
    assert clear.json()['version']==2
    with Session(engine) as session:
        assert session.scalar(select(m.User).where(m.User.username==payload['username'])).password_hash==stored_hash
    assert 'password' not in response.text
    assert api.put('/auth/me/profile',headers=admin,json={'expected_version':0,'email':'supervisor@example.test'}).status_code==200
    assert api.get('/auth/me/profile',headers=tech).json()['email'] is None
