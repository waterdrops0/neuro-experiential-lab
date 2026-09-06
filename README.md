# Neuro Experiential Control Lab — MVP v0.1

Aplicație desktop locală pentru un operator: monitorizare fiziologică simulată, cinci stări care controlează audio și haptics, markere și sesiuni persistente. Funcționează doar cu laptopul, fără cloud, conturi sau hardware suplimentar. Nu include VR.

**Toate profilurile și valorile sunt DEMO experimentale, fără recomandări sau afirmații medicale ori terapeutice.** Haptics este exclusiv o simulare vizuală; audio poate fi redat efectiv prin difuzoarele laptopului.

## Instalare

Python 3.12+ (versiunea verificată: 3.12). Din directorul proiectului:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Pe Linux, dacă lipsesc biblioteci Qt (Ubuntu/Debian):

```bash
sudo apt-get install libegl1 libopengl0 libxcb-cursor0 libxkbcommon-x11-0
```

Pe macOS folosește Python 3.12 și aceleași comenzi venv ca pe Linux. Instalarea inițială descarcă bibliotecile; rularea este complet offline. Nu sunt necesare fișiere audio: câmpul `file` gol activează tonuri sintetice cu amplitudine redusă.

## Operare

1. `START SESSION` creează un UUID, salvează configurația și activează SAFE cu fade.
2. Selectează SAFE, RESOURCE, PERSPECTIVE, INTEGRATION sau RETURN prin butoane ori tastele 1–5. Selectarea aceleiași stări reaplică profilul și creează marker, inclusiv după STOP.
3. `ADD MARKER` salvează nota opțională. `SAVE SUDS` înregistrează valoarea 0–10 într-un eveniment separat.
4. `PAUSE` oprește outputs, îngheață timpul activ și suspendă eșantioanele. Graficele continuă live. Markerele sunt permise și în pauză, cu timestamp absolut. `RESUME` reia înregistrarea; reaplică explicit o stare pentru audio/haptics.
5. `STOP OUTPUTS` sau ESC oprește imediat ambele outputs, inclusiv fade-urile în curs. Senzorul și înregistrarea continuă. Starea selectată rămâne vizibilă, dar profilurile efective din log sunt OFF.
6. `END SESSION` oprește outputs și închide fișierele. Închiderea ferestrei finalizează sesiunea la fel.

Poți testa stările și fără sesiune, dar înregistrarea începe doar la START. Tastele numerice sunt suspendate în câmpurile de introducere a notelor/SUDS; ESC rămâne disponibil. Audio pornește doar la START sau la selectarea explicită a unei stări. Lipsa dispozitivului audio apare ca ERROR / NO DEVICE, fără blocarea monitorizării. `python app.py --no-audio` dezactivează explicit sunetul.

## Configurare

Editează `config/states.json`, apoi repornește aplicația. Sunt obligatorii exact cele cinci chei. Exemplu de profil:

```json
{
  "name": "SAFE",
  "audio": {
    "file": "",
    "volume": 0.25,
    "fade_in": 2.0,
    "fade_out": 1.5,
    "loop": true
  },
  "haptic": {
    "profile": "steady_low",
    "intensity": 0.2,
    "frequency": 35,
    "pattern": "steady",
    "fade_in": 2.0,
    "fade_out": 1.0
  }
}
```

`file`: cale WAV/MP3 absolută sau relativă la proiect; gol = ton demo. Un fișier explicit lipsă produce eroare audio, fără înlocuire silențioasă cu ton. `volume` și `intensity`: 0–1; fade-uri în secunde, nenegative. `frequency`: Hz simulați; `pattern`: `steady`, `pulse`, `wave`. Indicatorul arată anvelopa lentă, nu oscilația de 30–45 Hz. Haptics reduce întâi intensitatea veche prin fade-out, apoi crește către noua intensitate. Audio folosește canale suprapuse pentru crossfade.

`config/settings.json`: refresh UI 2–5 Hz (implicit 4), fereastra graficelor 120 s, timeout senzor 4 s, directorul sesiunilor, activarea audio. Configurația este validată la pornire. Nu se reîncarcă în timpul unei sesiuni. Datele RMSSD folosesc ultimele 60 de intervale RR; prima bătaie afișează „—”.

## Date și recuperare

Fiecare `data/sessions/<session_id>/` conține:

- `samples.csv`: timestamp UTC ISO 8601, timp activ, HR, RR, RMSSD, calitate, stare și profilurile efective, intensitate haptics normalizată 0–1.
- `events.csv`: timestamp, timp activ, tip, stare anterioară/nouă, notă. Include START/PAUSE/RESUME/END, schimbări de stare, STOP, deconectări, markere și SUDS.
- `session.sqlite3`: tabele `session`, `samples`, `events`, cu aceleași înregistrări.
- `configuration.json`: configurația folosită în acea sesiune.

Se înregistrează fiecare bătaie nouă, nu copii ale ultimului RR la fiecare refresh UI. CSV se flush-uiește și SQLite se commit-uiește după fiecare rând. O oprire forțată poate lăsa sesiunea marcată RUNNING; datele deja scrise rămân inspectabile. CSV și SQLite sunt două destinații independente, fără tranzacție atomică comună; eroarea uneia este afișată, cealaltă continuă. Nu există încă instrument automat de reconciliere. Excepțiile sunt în `data/application.log`, cu rotație. Directorul datelor este exclus din git.

## Arhitectură

- `core/control_engine.py`: starea și comenzile comune pentru outputs.
- `core/event_bus.py`: pub/sub sincron, izolează erorile abonaților.
- `core/session_manager.py`: lifecycle, timp monotonic, markere, persistare.
- `core/models.py`: modelul de eșantion, UTC și validare.
- `sensors/base.py`, `simulator.py`: contract și simulator cu drift lent, modulație respiratorie, zgomot mic, RR corelat cu HR și RMSSD.
- `audio/audio_engine.py`: pygame mixer, WAV/MP3, tonuri, loop, volum, fade și stop.
- `haptics/`: contract, simulator de anvelopă și stub de transducer.
- `ui/`: dashboard, grafice pyqtgraph, comenzi și adaptoare pentru evenimente.
- `storage/`: CSV și SQLite.

Evenimente: `physiological_data_updated`, `state_changed`, `session_started`, `session_ended`, `marker_added`, `audio_profile_changed`, `haptic_profile_changed`, `outputs_stopped`, `storage_error`. Interfața primește `SensorProvider` prin injecție; nu depinde de modelul simulatorului. Tick-ul Qt face polling neblocant și actualizează outputs/UI. Adapterele reale trebuie să ruleze I/O în worker și să livreze date prin coadă, fără acces direct la widgeturi.

## Extindere hardware

**Polar H10:** implementează `PolarH10Provider.connect/poll/disconnect` în `sensors/polar_h10.py`, cu client BLE într-un worker. Decodează HR și RR, convertește intervalele în ms, păstrează momentul achiziției, calculează RMSSD și raportează calitatea/staleness. Înlocuiește instanța simulatorului în composition root (`app.py`). Stub-ul actual refuză conectarea explicit; nu pretinde că există hardware. Un EEGProvider poate folosi același lifecycle, cu modele și evenimente suplimentare pentru canale EEG, fără a forța EEG în câmpuri HR/RR.

**Controller USB/MIDI:** creează un adapter separat care citește dispozitivul într-un worker. Mapează mesajele/butoanele la `ControlEngine.change_state` și `stop_outputs`, prin Qt queued signals către firul GUI. Adaugă debounce și teste pentru comenzi duplicate. Tastatura laptopului este controllerul funcțional al MVP-ului.

**Transducer separat:** implementează `AudioTransducerHapticOutput` cu un dispozitiv audio dedicat, de exemplu prin sounddevice, separat de mixerul programului audio. Adaugă selecția explicită a ieșirii, generarea semnalului, limite de amplitudine, watchdog și mute imediat. Nu trimite automat semnalul haptic către difuzoarele laptopului. Verificarea pe hardware real rămâne necesară; stub-ul nu emite semnal.

## Testare

```bash
python -m pytest -q
```

Testele GUI/audio folosesc backend-uri offscreen/dummy; nu redau sunet. Verifică RMSSD, modelul simulat, configurația, tranzițiile, fade, sesiuni/pauză, CSV/SQLite, erori, comenzi GUI, ESC și deconectarea.

Smoke test fără display și fără ieșire audio fizică (Linux/macOS):

```bash
QT_QPA_PLATFORM=offscreen SDL_AUDIODRIVER=dummy python app.py --smoke-test --session-dir /tmp/neuro-smoke
```

Acesta pornește o sesiune, schimbă starea, adaugă marker, oprește outputs și închide după aproximativ 3 secunde. Pentru verificare interactivă, rulează simplu `python app.py`.

## Limitări

Simularea fiziologică nu este un instrument de măsurare și calitatea semnalului este scenarizată. Nu există integrare BLE/MIDI/transducer efectivă, EEG sau display separat. Planificarea Qt și pygame nu oferă latență deterministă ori sincronizare hardware. Fișierele audio sunt încărcate în memorie; folosește clipuri scurte/moderate (MP3 depinde de suportul SDL_mixer al platformei). La schimbări extrem de rapide sunt disponibile 16 canale, apoi cel mai vechi este oprit. Nu există export clinic, analiză retrospectivă sau criptare integrată. Configurația și GUI au fost proiectate pentru lucru local, cu un singur operator.

Documentație pentru bibliotecile folosite: [pygame mixer](https://www.pygame.org/docs/ref/mixer.html), [pyqtgraph](https://pyqtgraph.readthedocs.io/en/pyqtgraph-0.13.7/).
