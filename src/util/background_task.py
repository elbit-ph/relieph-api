import asyncio


async def save_headline_data():
    logger.info("Saving headline data to the database...")
    # Your code to save headline data to the database
    logger.info("Headline data saved successfully.")

def schedule_save_headline_data():
    asyncio.create_task(save_headline_data())
    # Schedule the task to run again after 1 hour
    asyncio.create_task(asyncio.sleep(3600)).add_done_callback(lambda _: schedule_save_headline_data())

async def start_model():
    logger.info("Application started.")
    # Schedule the first execution of the task
    asyncio.create_task(asyncio.sleep(5)).add_done_callback(lambda _: schedule_save_headline_data())

