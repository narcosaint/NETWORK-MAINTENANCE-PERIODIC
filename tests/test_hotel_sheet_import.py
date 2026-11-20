from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
import sys,uuid
import pytest
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.models import Base,Hotel
spec=spec_from_file_location('hotel_import',ROOT/'scripts/import_hotels_sheet.py');mod=module_from_spec(spec);spec.loader.exec_module(mod)


def test_additive_import_is_idempotent_and_preserves_old_fields():
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    existing_id=uuid.uuid4();mapping={'FAVE HOTEL':{'id':str(existing_id),'expected_name':'Favehotel MEX Tunjungan'}}
    rows=[{'source_sheet':name,'name':name,'address':'Original sheet address '+name,'customer_name':'Customer '+name}
          for name in ('FAVE HOTEL','CROWN','GRAHA PENA LT3','GRAHA PENA LT5')]
    manifest={'spreadsheet_id':'QA fixture only','rows':rows}
    with Session(engine) as session:
        session.add(Hotel(id=existing_id,name='Favehotel MEX Tunjungan',address='Existing reviewed address'));session.commit()
        plan=mod.import_hotels(session,manifest,'all',mapping)
        assert len(list(session.scalars(select(Hotel))))==1
        assert [a['action'] for a in plan]==['fill_missing','create','create','create']
        applied=mod.import_hotels(session,manifest,'all',mapping,apply=True);session.commit()
        old=session.get(Hotel,existing_id)
        assert old.address=='Existing reviewed address' and old.name=='Favehotel MEX Tunjungan'
        assert old.customer_name=='Customer FAVE HOTEL'
        assert len(list(session.scalars(select(Hotel))))==4
        assert all(a['action']=='keep' for a in mod.import_hotels(session,manifest,'all',mapping,apply=True));session.commit()
        assert len(mod.plan_import(session,manifest,'hotels',mapping))==2
        assert applied[2]['id']!=applied[3]['id'] # Different physical branches stay separate.
        with pytest.raises(ValueError,match='Reviewed match changed'):
            mod.plan_import(session,manifest,'all',{'FAVE HOTEL':{'id':str(existing_id),'expected_name':'Wrong'}})
        with pytest.raises(ValueError):mod.plan_import(session,manifest,'unconfirmed')
    engine.dispose()


def test_ambiguous_and_repeated_sources_cannot_be_imported():
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    row={'source_sheet':'CROWN','name':'CROWN','address':'QA address','customer_name':'QA customer'}
    with Session(engine) as session:
        session.add_all([Hotel(name='Crown'),Hotel(name='CROWN')]);session.commit()
        with pytest.raises(ValueError,match='Ambiguous'):mod.plan_import(session,{'spreadsheet_id':'qa','rows':[row]},'all')
    engine.dispose()
