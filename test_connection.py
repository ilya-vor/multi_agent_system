import asyncio
import logging
from spade import agent
from spade.behaviour import CyclicBehaviour

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class TestAgent(agent.Agent):
    class TestBehaviour(CyclicBehaviour):
        async def run(self):
            print("✓ Агент успешно подключен и работает!")
            await asyncio.sleep(5)
            self.kill()

    async def setup(self):
        print("Настройка агента...")
        self.add_behaviour(self.TestBehaviour())


async def main():
    jid = "test@DESKTOP-ILYA"
    password = "password"  # Замените на реальный пароль

    print(f"Попытка подключения к DESKTOP-ILYA с JID: {jid}")

    # Создаем агента с отключенным TLS
    test_agent = TestAgent(
        jid=jid,
        password=password,
        port=5222,
    )

    try:
        await test_agent.start(auto_register=True)
        print("Агент запущен, ожидаем подключения...")

    except Exception as e:
        print(f"✗ Ошибка при подключении: {e}")

    finally:
        try:
            await test_agent.stop()
            print("Агент остановлен")
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())