# Multfilm studio

Qisqa vertikal multfilm videolar yasash uchun skillar, kod va avtomatlar. Hammasi bepul vositalarda ishlaydi.

## Ichida nima bor

| Papka | Nima |
|---|---|
| `.claude/skills/cartoon-3d-short` | **3D dunyoda 2D personajlar** uslubi (three.js + Remotion). Manba: github.com/mromidev/claude-animated-shorts (MIT). Boshqa kanal kadrlari ataylab qo'shilmagan. |
| `.claude/skills/cartoon-reel` | **Tekis 2D multfilm** reels (30 s): personajlar, olomon, raqam hisoblagich, 2–3 so'zli yozuvlar. |
| `tools/remotion-cartoon` | Ishlaydigan Remotion loyihasi. Birinchi video: **Pet Rock** (apex_wealths, 2026-11-14). |
| `tools/cartoon-reel` | 2D reels yasovchi Python kodi (Pillow + ffmpeg). |
| `tools/voice` + `.github/workflows/voice.yml` | O'zbekcha ovoz (Microsoft Edge, `uz-UZ-SardorNeural`) va so'zlar vaqti (`words.json`). |
| `voices/<nom>/script.txt` | Ovoz matni. Push qilinsa, GitHub o'zi `voice.mp3` va `words.json` yaratadi. |

## Yangi 3D multfilm video — qadamlar

1. **Hikoya**: bitta tekshirilgan fakt (2024-yildan oldingi), raqamlar so'z bilan yoziladi. Ochiq savol bilan boshlash yaxshi ishlaydi.
2. **Ovoz**: `voices/<nom>/script.txt` yozing va push qiling → Actions "Ovoz yaratish" ishlaydi → `voice.mp3` + `words.json` repoga qaytadi.
3. **Sahna**: `tools/remotion-cartoon/src/petrock` ni `src/<nom>` ga nusxalang. `story.ts` da kadrlarni (`SHOTS`) so'z raqamlariga bog'lang (`W(i)` — i-so'z boshlanadigan kadr). `world.ts` da joy va buyumlarni, `cards.ts` da personajlarni o'zgartiring. `Root.tsx` ga yangi kompozitsiya qo'shing.
4. **Musiqa**: `python3 audio/petrock_music.py src/<nom>/words.json out/music.wav` (o'zimiz sintez qilgan, mualliflik muammosi yo'q).
5. **Render** (GPU shart emas):
   ```sh
   cd tools/remotion-cartoon && npm install
   npx remotion still src/index.ts PetRock out/test.png --frame=60 --scale=0.5 --gl=swangle --browser-executable=<chrome-headless-shell>
   npx remotion render src/index.ts PetRock out/raw.mp4 --codec=h264 --crf=18 --gl=swangle --browser-executable=<chrome-headless-shell> --concurrency=4
   ffmpeg -i out/raw.mp4 -i public/voice/<nom>.mp3 -i out/music.wav -filter_complex "[2]volume=0.16[m];[1][m]amix=inputs=2:duration=first[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k out/final.mp4
   ```
6. **Joylash**: tayyor mp4 apex_wealths navbatiga (`shorts-agent`) yoki qo'lda yuklanadi.

## Muhim eslatmalar

- Dasturiy grafikada (GPU'siz) post-effektlar ishlamaydi, shuning uchun qora konturlar `outline.ts` dagi usul bilan chiziladi.
- Remotion jismoniy shaxslar va 3 kishigacha bo'lgan kompaniyalar uchun bepul.
- Videoda faqat tekshirilgan faktlar; boshqa kanallarning ssenariysi, personaji yoki kadri ishlatilmaydi.
