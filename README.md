# DAUYS-BOT
##cursor жобаға осындай туториал жазып берді

Telegram бот: қазақша мәтінді дауысқа айналдырады (TTS) және дауысты мәтінге танытады (STT). Мәтін жіберсең — аудио келеді, аудио жіберсең — танылған мәтін қайта дыбысталады.

Бот пен STT **Vercel**-де іске қосылады. Төменде **Vercel CLI** арқылы нөлден деплойға дейінгі толық қадамдар берілген.

---

## Алдын ала дайындық

Деплойға кіргізбес бұрын мыналар дайын болу керек:

| Қажет | Сипаттама |
|-------|-----------|
| **Node.js** | Vercel CLI үшін. [nodejs.org](https://nodejs.org) — LTS нұсқасын орнатыңыз. |
| **Git** | Репозиторийді клондау үшін. |
| **Vercel тіркелгі** | [vercel.com](https://vercel.com) — тіркеліп, логин болыңыз. |
| **Telegram бот токены** | [@BotFather](https://t.me/BotFather) → `/newbot` → алынған токенді сақтаңыз. |
| **MongoDB URI** | [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) немесе басқа сервисте кластер жасап, байланыс жолын (мысалы `mongodb+srv://user:pass@cluster.mongodb.net/`) көшіріңіз. |
| **Telegram user id (админ)** | Бот сізді админ ретінде тануы үшін. Мысалы [@userinfobot](https://t.me/userinfobot) арқылы ID алып, сақтаңыз. |

---

## 1. Vercel CLI орнату және логин

Терминалда (PowerShell немесе CMD):

```bash
npm install -g vercel
```

Орнатылғаннан кейін Vercel тіркелгісіне кіріңіз:

```bash
vercel login
```

Браузер ашылып, email арқылы растау сұрайды. Аяқтаған соң терминалда «Logged in» көрінеді.

---

## 2. Жобаны жерге клондау

Репозиторийді клондап, папкаға кіріңіз:

```bash
git clone https://github.com/davidsuragan/dauys-bot.git
cd dauys-bot
```

---

## 3. STT сервисін Vercel-ге деплой (CLI)

STT — аудионы мәтінге айналдыратын API. Алдымен оны деплой етіп, URL аламыз; кейін ботта `STT_API_URL` ретінде қолданамыз.

**3.1.** `stt` папкасына кіріңіз:

```bash
cd stt
```

**3.2.** Бірінші рет деплой (проект жасалады, сілтеме беріледі):

```bash
vercel
```

Сұрақтар шығады:
- **Set up and deploy?** — `Y` (Yes).
- **Which scope?** — өз тіркелгіңізді таңдаңыз.
- **Link to existing project?** — `N` (жаңа проект).
- **Project name?** — мысалы `dauys-stt` (Enter басып әдепкіні де қалдыруға болады).
- **Directory?** — `.` (нүкте, яғни ағымдағы `stt` папкасы).

Деплой аяқталғанда терминалда сілтеме шығады, мысалы:

```
Production: https://dauys-stt-xxxx.vercel.app
```

Бұл сілтемені **бүтіндей** көшіріп, қағазға немесе файлға жазыңыз. Кейін ботта `STT_API_URL` осы сілтеме + `/api/stt` болады:

```
https://dauys-stt-xxxx.vercel.app/api/stt
```

**3.3.** Production-ге шығару (міндетті емес, бірақ тұрақты URL керек болса):

```bash
vercel --prod
```

Одан кейін `stt` деплойы дайын. Бот папкасына қайтыңыз:

```bash
cd ..
```

---

## 4. Ботты Vercel-ге деплой (CLI)

**4.1.** `bot` папкасына кіріңіз:

```bash
cd bot
```

**4.2.** Орта айнымалыларын қосу (Vercel CLI арқылы).

Әр айнымалы үшін бір рет `vercel env add` орындаңыз. Мән сұрағанда жазып Enter басыңыз. «Which environment?» дегенде **Production** таңдаңыз (P басыңыз).

```bash
vercel env add BOT_TOKEN
```
Мән: BotFather-дан алынған токен (мысалы `123456789:AAH...`).

```bash
vercel env add MONGODB_URI
```
Мән: MongoDB байланыс жолы (мысалы `mongodb+srv://user:pass@cluster.mongodb.net/`).

```bash
vercel env add ADMIN_IDS
```
Мән: Админдердің Telegram user id-лері, үтірмен бір жолда (мысалы `123456789,987654321`).

```bash
vercel env add STT_API_URL
```
Мән: 3-қадамдағы STT сілтеме + `/api/stt` (мысалы `https://dauys-stt-xxxx.vercel.app/api/stt`).

**4.3.** Ботты деплой ету:

```bash
vercel
```

Сұрақтар: жаңа проект — `N`, проект аты — мысалы `dauys-bot`, directory — `.`.

**4.4.** Production-ге шығару (орта айнымалылары production-да қолданылады):

```bash
vercel --prod
```

Аяқталғанда мына тәрізді сілтеме шығады:

```
Production: https://dauys-bot-xxxx.vercel.app
```

Бұл — боттың негізгі URL-і.

---

## 5. Telegram webhook орнату

Бот хабарламаларды қабылдайтын болуы үшін Telegram-ға webhook айту керек. Браузерде мына сілтемені ашыңыз (өз бот URL-іңізбен ауыстырыңыз):

```
https://dauys-bot-xxxx.vercel.app/set_webhook
```

Сілтемеде `dauys-bot-xxxx` орнына 4-қадамда шыққан нақты доменіңізді жазыңыз.

Жауапта `"ok": true` көрінсе webhook орнатылды. Кейін Telegram-да ботты ашып `/start` жіберіп тексеріңіз.

---

## 6. Кейін өзгерістерді жаңарту (деплой қайталау)

Кодта өзгеріс жасаған соң деплойды қайта орындаңыз.

**STT жаңарту:**

```bash
cd dauys-bot/stt
vercel --prod
```

**Бот жаңарту:**

```bash
cd dauys-bot/bot
vercel --prod
```

Webhook қайта орнату қажет емес — URL өзгермесе Telegram сол адресіне жіберіп тұрады.

---

## 7. Орта айнымалыларын өзгерту (бот)

Жаңа токен немесе MongoDB қойғыңыз келсе:

```bash
cd bot
vercel env rm BOT_TOKEN production
vercel env add BOT_TOKEN
```

Содан кейін қайта деплой:

```bash
vercel --prod
```

Басқа айнымалылар үшін де `vercel env rm` / `vercel env add` осылай қолданылады. Тізімді көру: `vercel env ls`.

---

## Қысқаша қадамдар (электрондық кесте ретінде)

| # | Қадам | Команда / әрекет |
|---|--------|-------------------|
| 1 | Vercel CLI орнату | `npm install -g vercel` |
| 2 | Логин | `vercel login` |
| 3 | Клондау | `git clone <repo>` → `cd dauys-bot` |
| 4 | STT деплой | `cd stt` → `vercel` → `vercel --prod` → URL-ді жазу |
| 5 | Бот env | `cd bot` → `vercel env add BOT_TOKEN` (және MONGODB_URI, ADMIN_IDS, STT_API_URL) |
| 6 | Бот деплой | `vercel` → `vercel --prod` |
| 7 | Webhook | Браузерде `https://...vercel.app/set_webhook` ашу |

---

## Ескертпелер

- TTS бот ішінде Piper арқылы жұмыс істейді (`bot/piper_bin`), сондықтан бөлек TTS сервисін Vercel-ге қосу қажет емес.
- STT Google Speech Recognition (kk-KZ) қолданады; квота шектеулері болуы мүмкін.
- Бот `vercel.json` бойынша `maxDuration: 60` секунд — ұзақ синтездер үшін.

Автор: **@davidsuragan**. Арна: [Дәуіт Сұраған](https://t.me/davidsuragan).
