from typing import List
import typing

import asyncio

from fastapi import FastAPI

from icalendar import Calendar, Event

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse





import strawberry
from strawberry.fastapi import GraphQLRouter

## Definice GraphQL typu (pomoci strawberry https://strawberry.rocks/)
## Strawberry zvoleno kvuli moznosti mit federovane GraphQL API (https://strawberry.rocks/docs/guides/federation, https://www.apollographql.com/docs/federation/)
from gql_events.GraphTypeDefinitions import Query

## Definice DB typu (pomoci SQLAlchemy https://www.sqlalchemy.org/)
## SQLAlchemy zvoleno kvuli moznost komunikovat s DB asynchronne
## https://docs.sqlalchemy.org/en/14/core/future.html?highlight=select#sqlalchemy.future.select
from gql_events.DBDefinitions import startEngine, ComposeConnectionString

## Zabezpecuje prvotni inicializaci DB a definovani Nahodne struktury pro "Univerzity"
# from gql_workflow.DBFeeder import createSystemDataStructureRoleTypes, createSystemDataStructureGroupTypes

connectionString = ComposeConnectionString()


def singleCall(asyncFunc):
    """Dekorator, ktery dovoli, aby dekorovana funkce byla volana (vycislena) jen jednou. Navratova hodnota je zapamatovana a pri dalsich volanich vracena.
    Dekorovana funkce je asynchronni.
    """
    resultCache = {}

    async def result():
        if resultCache.get("result", None) is None:
            resultCache["result"] = await asyncFunc()
        return resultCache["result"]

    return result

from gql_events.DBFeeder import initDB

@singleCall
async def RunOnceAndReturnSessionMaker():
    """Provadi inicializaci asynchronniho db engine, inicializaci databaze a vraci asynchronni SessionMaker.
    Protoze je dekorovana, volani teto funkce se provede jen jednou a vystup se zapamatuje a vraci se pri dalsich volanich.
    """
    print(f'starting engine for "{connectionString}"')

    import os
    makeDrop = os.environ.get("DEMO", "") == "true"
    if makeDrop:
        print("drop data")
    else:
        print("keep data")
    result = await startEngine(
        connectionstring=connectionString, makeDrop=makeDrop, makeUp=True
    )

    print(f"initializing system structures")

    ###########################################################################################################################
    #
    # zde definujte do funkce asyncio.gather
    # vlozte asynchronni funkce, ktere maji data uvest do prvotniho konzistentniho stavu
    await initDB(result)
    # await asyncio.gather( # concurency running :)
    # sem lze dat vsechny funkce, ktere maji nejak inicializovat databazi
    # musi byt asynchronniho typu (async def ...)
    # createSystemDataStructureRoleTypes(result),
    # createSystemDataStructureGroupTypes(result)
    # )

    ###########################################################################################################################
    print(f"all done")
    return result


from strawberry.asgi import GraphQL

from gql_events.Dataloaders import createLoaders_3
class MyGraphQL(GraphQL):
    """Rozsirena trida zabezpecujici praci se session"""

    async def __call__(self, scope, receive, send):
        asyncSessionMaker = await RunOnceAndReturnSessionMaker()
        async with asyncSessionMaker() as session:
            self._session = session
            self._user = {"id": "?"}
            return await GraphQL.__call__(self, scope, receive, send)

    async def get_context(self, request, response):
        parentResult = await GraphQL.get_context(self, request, response)
        asyncSessionMaker = await RunOnceAndReturnSessionMaker()
        return {
            **parentResult,
            "session": self._session,
            "asyncSessionMaker": asyncSessionMaker,
            "user": self._user,
            "all": await createLoaders_3(asyncSessionMaker)
        }


from gql_events.GraphTypeDefinitions import schema

## ASGI app, kterou "moutneme"
graphql_app = MyGraphQL(schema, graphiql=True, allow_queries_via_get=True)

app = FastAPI()
app.mount("/gql", graphql_app)



from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.post("/ical")
async def create_ical():
    try:
        # Set the iCal data as a string
        ical_data = """
        BEGIN:VCALENDAR
        VERSION:2.0
        PRODID:-//hacksw/handcal//NONSGML v1.0//EN
        BEGIN:VEVENT
        UID:uid1@example.com
        DTSTAMP:19970714T170000Z
        ORGANIZER;CN=<link>John Doe</link>:MAILTO:john.doe@example.com
        DTSTART:19970714T170000Z
        DTEND:19970715T040000Z
        SUMMARY:Bastille Day Party
        GEO:48.85299;2.36885
        END:VEVENT
        END:VCALENDAR
        """

        # Set the appropriate response headers
        headers = {
            "Content-Disposition": "attachment; filename=calendar.ics",
            "Content-Type": "text/calendar",
        }

        # Return the iCal data as the response
        return PlainTextResponse(ical_data, headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ical")
async def get_ical():
    ical_data = """BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Example Corp//Calendar Application//EN\r\nBEGIN:VEVENT\r\nUID:9876543210\r\nDTSTAMP:20230215T150000Z\r\nDTSTART:20231224T180000Z\r\nDTEND:20231224T200000Z\r\nSUMMARY:Christmas Eve Celebration\r\nDESCRIPTION:Join us for a festive Christmas Eve celebration filled with joy and merriment.\r\nLOCATION:Your Home\r\nEND:VEVENT\r\nEND:VCALENDAR"""
    return PlainTextResponse(ical_data, media_type="text/calendar")
@app.on_event("startup")
async def startup_event():
    initizalizedEngine = await RunOnceAndReturnSessionMaker()
    return None


print("All initialization is done")

@app.get('/hello')
def hello():
    return {'ICAL': 'FORMAT',
            'BEGIN': 'VCALENDAR'}

###########################################################################################################################
#
# pokud jste pripraveni testovat GQL funkcionalitu, rozsirte apollo/server.js
#
###########################################################################################################################
