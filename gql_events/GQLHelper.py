from ics import Calendar, Event
import asyncpg


def initEventData(event):
    ev = Event()
    ev.name = event[0]
    ev.description = event[1]
    ev.begin = event[2]
    ev.enddate = event[3]

    return ev

async def user_exists(connection, token):

    query = "SELECT masterevent_id FROM exported_users WHERE public_token = $1"
    result = await connection.fetch(query, token)

    if not result:
        #user not found or bad token
        return 0
    else:
        return result[0]['masterevent_id']




async def get_Events(token: str):
    
    calend = Calendar()
    try:
        conString = "postgresql://postgres:example@localhost:5432/data"
        pool = await asyncpg.create_pool(conString)

        async with pool.acquire() as connection:
            # result_token = await connection.fetch(f"SELECT * FROM exported_users WHERE public_token = '{token}'")
            # master_ID = result_token[0]['masterevent_id']

            master_ID = await user_exists(connection, token)

            if master_ID is not 0:
                query = "SELECT id, name, startdate, enddate FROM events WHERE masterevent_id = $1"
                results = await connection.fetch(query, master_ID)
            else:
                print("user not found")
                return  calend
        await pool.close()
    except:
        print("woops, something went awry")
        results = None

    if  results != None:
        for result in results:
            # calling function that filters the query
            # (hmmm, maybe change the query itself to pickup only the required
            # data)
            # edit - done :)
            calend.events.add(initEventData(result))
        return calend
    
    else:

        print("There was no result or the result was not whole, please consult the one who made this spaghetti.")

        return calend
