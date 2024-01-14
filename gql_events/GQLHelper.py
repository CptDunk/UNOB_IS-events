from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse

from fastapi.responses import FileResponse
from ics import Calendar, Event
import os
from gql_events.DBDefinitions import ComposeConnectionString
import asyncpg
import json

# new test of GQL model to help retrieve information from resolver function 
class testEvent:
    id: str
    name: str
    lastchange: str
    startdate: str
    enddate: str
    
    


async def get_Events():
    # will be used to return a list of testEvent objects?
    #testList = []

    calend = Calendar()

    conString = "postgresql://postgres:example@localhost:5432/data"
    
    pool = await asyncpg.create_pool(conString)
    
    async with pool.acquire() as connection:
        try:
            with open('written_events.json', 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("File not found or empty")
            query = "SELECT * FROM events"
            data = {}
        else:
            if data == {}:
                print("File is empty. Fetching all events.")
                query = "SELECT * FROM events"
            else:
                conditions = []
                ids = []
                for id, timestamp in data.items():
                    conditions.append(f"(id = '{id}' AND lastchange > '{timestamp}')")
                    ids.append(f"'{id}'")
                conditions.append(f"id NOT IN ({', '.join(ids)})")
                query = f"SELECT * FROM events WHERE {' AND '.join(conditions)}"
                #print(query)
        results = await connection.fetch(query)

    await pool.close()

    try:
        with open('dummy_calendar.ics', 'r') as f:
            if os.stat('dummy_calendar.ics').st_size == 0:
                print("File is empty")
                calend = Calendar()
            else:
                calend = Calendar(f.read())
    except FileNotFoundError:
        print("File not found")
        calend = Calendar()

    #TODO probably would be separate function
    for result in results:
        # Check if event already exists -> 'ev'
        existing_event = next((ev for ev in calend.events if ev.name == result['id']), None)
        if existing_event:
            # Update existing event
            existing_event.description = result['name'] + "; Last: "+ str(result['lastchange'].serialize())
            existing_event.begin = result['startdate']
            existing_event.end = result['enddate']
        else:
            
            # Create new event 'nev'
            nev = Event()
            nev.name = result['id']
            nev.description = result['name'] + "Last:"+ str(result['lastchange'])
            nev.begin = result['startdate']
            nev.end = result['enddate']
            calend.events.add(nev)
            
            #test of the new model testEvent(works, but must always delete written_events.json)
            """
            testEvent = testEvent()
            testEvent.id = result['id']
            testEvent.name = result['name']
            testEvent.lastchange = str(result['lastchange'])
            testEvent.startdate = result['startdate']
            testEvent.enddate = result['enddate']

            testList.append(testEvent)
""" 


        data[result['id']] = str(result['lastchange'])

    # Write the updated calendar back to the file, return complete
        
    with open('dummy_calendar.ics', 'w') as f:
        f.write(calend.serialize())
        
    with open('written_events.json', 'w') as f:
        json.dump(data, f)

    #return testList

    # Old code, was overwriting file every time, without preserving existing events
    """
    with open('dummy_calendar.ics', 'w') as f:
        for result in results:
            e = Event()
            e.name = result['id']
            e.description = result['name'] + "Last:"+ str(result['lastchange'])
            e.begin = result['startdate']
            e.end = result['enddate']
            c.events.add(e)
            data[result['id']] = str(result['lastchange'])

        f.writelines(c)
         
    with open('written_events.json', 'w') as f:
        json.dump(data, f)
   """