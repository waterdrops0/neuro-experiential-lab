# Verificare MVP

Mediu: Linux x86_64, Python 3.12.14, PySide6 6.8.3, pygame 2.6.1.

- `python -m pytest -q`: 10 teste trecute (nucleu, storage, simulator, GUI și audio dummy).
- `QT_QPA_PLATFORM=offscreen SDL_AUDIODRIVER=dummy python app.py --smoke-test`: exit 0; sesiune ENDED, 3 eșantioane și 7 evenimente; numărul eșantioanelor CSV/SQLite coincide.
- `QT_QPA_PLATFORM=offscreen python app.py --smoke-test`: exit 0 fără dispozitiv audio; eroare ALSA logată, sesiune ENDED, 3 eșantioane și 7 evenimente persistate.
- Dashboard randat offscreen și inspectat vizual la 1380×880.

Nu s-a verificat sunetul prin difuzoare fizice, nici hardware BLE/MIDI/haptic. Mesajul Qt offscreen `does not support propagateSizeHints` este emis de backend-ul de test.
