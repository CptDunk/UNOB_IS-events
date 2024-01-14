from typing import List
import typing

import asyncio

from fastapi import FastAPI


from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse





import strawberry
from strawberry.fastapi import GraphQLRouter

## Definice GraphQL typu (pomoci strawberry https://strawberry.rocks/)
## Strawberry zvoleno kvuli moznosti mit federovane GraphQL API (https://strawberry.rocks/docs/guides/federation, https://www.apollographql.com/docs/federation/)
from gql_events.GraphTypeDefinitions import Query

## Definice DB typu (pomoci SQLAlchemy https://www.sqlalchemy.org/)
## SQLAlchemy zvoleno kvuli moznost komunikovat s DB asynchronne
## https://docs.sqlalchemy.org/en/14/core/future.html?highlight=select#sqlalchemy.future.select
from gql_events.DBDefinitions import startEngine, ComposeConnectionString, EventModel

## Zabezpecuje prvotni inicializaci DB a definovani Nahodne struktury pro "Univerzity"
# from gql_workflow.DBFeeder import createSystemDataStructureRoleTypes, createSystemDataStructureGroupTypes

connectionString = ComposeConnectionString()
session = None

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




from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
import os
import gql_events.GQLHelper as Helper

@app.get("/ical")
async def get_ical():
    
    await Helper.get_Events()
    """
    endList = await Helper.get_Events()
    if endList != None:
        for object in endList:
            print(object)
            print(object.name)
            print(object.startdate)
            print(object.enddate)
            print(object.lastchange)
            print(object.id)
            print("")
    """
    file_name = "dummy_calendar.ics"
    file_path = os.path.join(os.getcwd(), file_name)
    

    # Stream the file to the client
    if os.path.exists(file_path):
        file_like = open(file_path, mode="rb")
        response = StreamingResponse(file_like, media_type="text/calendar")
        response.headers["Content-Disposition"] = f"attachment; filename={file_name}"
        return response
    else:
        return Response("File not found", status_code=404)


"""
@app.get("/gql")
async def graphiql(request: Request):
    return await graphql_app.render_graphql_ide(request)
"""

@app.on_event("startup")
async def startup_event():
    initizalizedEngine = await RunOnceAndReturnSessionMaker()
    session = initizalizedEngine
    return None


print("All initialization is done")
