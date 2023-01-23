import json
import os

from fastapi import FastAPI
from sqlalchemy import Column, Integer, \
    ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from src.fastapi_quickcrud.crud_router import crud_router_builder

TEST_DATABASE_URL = os.environ.get('TEST_DATABASE_URL', 'postgresql://postgres:1234@127.0.0.1:5432/postgres')

app = FastAPI()

Base = declarative_base()
metadata = Base.metadata

from sqlalchemy import create_engine

engine = create_engine(TEST_DATABASE_URL, future=True, echo=True,
                       pool_use_lifo=True, pool_pre_ping=True, pool_recycle=7200)
session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_transaction_session():
    try:
        db = session()
        yield db
    finally:
        db.close()


class Parent(Base):
    __tablename__ = 'parent_m2o_back_populates'
    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey('child_m2o_back_populates.id'))
    child = relationship("Child", back_populates="parents")

class Child(Base):
    __tablename__ = 'child_m2o_back_populates'
    id = Column(Integer, primary_key=True)
    parents = relationship("Parent", back_populates="child")

crud_route_child = crud_router_builder(db_session=get_transaction_session,
                                       db_model=Child,
                                       prefix="/child",
                                       tags=["child"]
                                       )

crud_route_parent = crud_router_builder(db_session=get_transaction_session,
                                        db_model=Parent,
                                        prefix="/parent",
                                        tags=["parent"]
                                        )
from starlette.testclient import TestClient

[app.include_router(i) for i in [crud_route_parent, crud_route_child]]

client = TestClient(app)



def test_get_parent_many_with_join():
    headers = {
        'accept': '*/*',
        'Content-Type': 'application/json',
    }

    response = client.get('/parent?join_foreign_table=child_m2o_back_populates', headers=headers)
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "child_m2o_back_populates_foreign": [
                {
                    "id": 1
                }
            ],
            "child_id": 1
        },
        {
            "id": 2,
            "child_m2o_back_populates_foreign": [
                {
                    "id": 1
                }
            ],
            "child_id": 1
        },
        {
            "id": 3,
            "child_m2o_back_populates_foreign": [
                {
                    "id": 2
                }
            ],
            "child_id": 2
        },
        {
            "id": 4,
            "child_m2o_back_populates_foreign": [
                {
                    "id": 2
                }
            ],
            "child_id": 2
        }
    ]


    response = client.get('/parent/1?join_foreign_table=child_m2o_back_populates', headers=headers)
    assert response.status_code == 200
    assert response.json() == {
            "id": 1,
            "child_m2o_back_populates_foreign": [
                {
                    "id": 1
                }
            ],
            "child_id": 1
        }


def test_get_child_many_with_join():
    headers = {
        'accept': '*/*',
        'Content-Type': 'application/json',
    }

    response = client.get('/child?join_foreign_table=parent_m2o_back_populates', headers=headers)
    assert response.status_code == 200
    a = response.json()
    assert response.json() == [
        {
            "parent_m2o_back_populates_foreign": [
                {
                    "id": 1,
                    "child_id": 1
                },
                {
                    "id": 2,
                    "child_id": 1
                }
            ],
            "id": 1
        },
        {
            "parent_m2o_back_populates_foreign": [
                {
                    "id": 3,
                    "child_id": 2
                },
                {
                    "id": 4,
                    "child_id": 2
                }
            ],
            "id": 2
        }
    ]
    response = client.get('/child/1?join_foreign_table=parent_m2o_back_populates', headers=headers)
    assert response.status_code == 200
    a = response.json()

    assert response.json() == {
    "parent_m2o_back_populates_foreign": [
      {
        "id": 1,
        "child_id": 1
      },
      {
        "id": 2,
        "child_id": 1
      }
    ],
    "id": 1
  }


def test_get_child_many_without_join():
    headers = {
        'accept': '*/*',
        'Content-Type': 'application/json',
    }

    response = client.get('/parent', headers=headers)
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "child_id": 1
        },
        {
            "id": 2,
            "child_id": 1
        },
        {
            "id": 3,
            "child_id": 2
        },
        {
            "id": 4,
            "child_id": 2
        }
    ]


    response = client.get('/parent/1', headers=headers)
    assert response.status_code == 200
    assert response.json() == {
    "id": 1,
    "child_id": 1
  }

def test_get_parent_many_without_join():
    headers = {
        'accept': '*/*',
        'Content-Type': 'application/json',
    }

    response = client.get('/child', headers=headers)
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1
        },
        {
            "id": 2
        },
        {
            "id": 3
        },
        {
            "id": 4
        }
    ]

    response = client.get('/child/1', headers=headers)
    assert response.status_code == 200
    assert response.json() == {
    "id": 1
  }


def setup_module(module):
    Child.__table__.create(engine, checkfirst=True)
    Parent.__table__.create(engine, checkfirst=True)

    db = session()

    db.add(Child(id=1))
    db.add(Child(id=2))
    db.add(Child(id=3))
    db.add(Child(id=4))
    db.flush()
    db.add(Parent(id=1, child_id=1))
    db.add(Parent(id=2, child_id=1))
    db.add(Parent(id=3, child_id=2))
    db.add(Parent(id=4, child_id=2))

    db.commit()


def teardown_module(module):
    Parent.__table__.drop(engine, checkfirst=True)
    Child.__table__.drop(engine, checkfirst=True)



