import asyncio
import edge_tts

async def test():
    communicate = edge_tts.Communicate("Xin chào quý thầy cô và các bạn, đây là hệ thống EduSupportAI.", "vi-VN-NamMinhNeural")
    await communicate.save("/tmp/test_tts.mp3")
    print("TTS test generated successfully!")

if __name__ == "__main__":
    asyncio.run(test())
