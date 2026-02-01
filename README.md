# DAUYS-BOT

Қазақша мәтінді дауысқа айналдыру (TTS) және дауысты мәтінге таныту (STT)
мүмкіндіктері бар Telegram-бот.

## Мүмкіндіктер

- **TTS (Piper):** Мәтінді қазақша дыбыстау. Бот ішінде Piper арқылы жұмыс
  істейді.
- **STT:** Дауыстық хабарламаларды мәтінге айналдыру (Google Speech
  Recognition).

## Құрылымы

- `bot/` — Негізгі бот (Python, Aiogram). Vercel-де жұмыс істейді.
- `stt/` — Дауысты тану сервисі (Node.js). Vercel Functions-те орналасқан.

## Деплой (Vercel CLI)

### 0. Дайындық

Алдымен Vercel CLI орнатып, жүйеге кіріңіз:

```bash
npm install -g vercel
vercel login
```

### 1. STT Сервисін деплой жасау

Алдымен дауысты тану (STT) сервисін іске қосып, оның мекенжайын алуымыз керек:

```bash
cd stt
vercel --prod
```

Деплой аяқталған соң шыққан URL-ді (мысалы, `https://dauys-bot.vercel.app`)
көшіріп алыңыз. Бот үшін STT мекенжайы `https://dauys-bot.vercel.app/api/stt`
болады.

### 2. Ботты деплой жасау

`bot/` папкасына `.env` файлын жасап, барлық қажетті айнымалыларды жазыңыз (оның
ішінде 1-қадамдағы STT URL-ін қосуды ұмытпаңыз):

**Қажетті `.env` айнымалылары:**

```env
BOT_TOKEN=your_bot_token
MONGODB_URI=your_mongodb_uri
ADMIN_IDS=id1,id2
STT_API_URL=https://your-stt-url.vercel.app/api/stt
```

Содан кейін деплой жасаңыз:

```bash
cd ../bot
vercel --prod
```

### 3. Webhook орнату

Ботты белсендіру үшін браузерде `https://<bot-url>.vercel.app/set_webhook`
мекенжайын ашыңыз.

## Қолданылған ресурстар

- [Piper](https://github.com/rhasspy/piper) — Жергілікті (local) жылдам дауыс
  синтезі.
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition/) — Google
  Speech API арқылы қазақша дауысты тану.
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) — Бұлттық мәліметтер
  базасы.
- [FastAPI](https://fastapi.tiangolo.com/) &
  [Aiogram](https://docs.aiogram.dev/) — Боттың негізгі қаңқасы.

---

Авторы: [@daketeach](https://t.me/daketeach)\
Арна: [Дәуіт Сұраған](https://t.me/davidsuragan)
