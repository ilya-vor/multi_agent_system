import asyncio
import main1
import main2
import main3

async def run_all_parallel():
    await asyncio.gather(
        main1.start(),
        main2.start(),
        main3.start()
    )

if __name__ == "__main__":
    print("Запуск всех агентов параллельно...")
    asyncio.run(run_all_parallel())