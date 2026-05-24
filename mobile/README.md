# Track Mobile — Flutter App

Full native Android app for the Track adaptive fitness platform.

## Stack

| Layer | Tech |
|---|---|
| State management | Riverpod 2.x |
| Navigation | go_router |
| HTTP client | Dio (+ secure token storage) |
| Charts | fl_chart |
| Health data | health (Google Health Connect) |
| Animations | flutter_animate |

## First-time setup

```powershell
# 1. Verify Flutter is on PATH
flutter --version

# 2. Install dependencies
flutter pub get

# 3. Run on a connected device or emulator
flutter run

# 4. Run on a specific device
flutter devices          # list devices
flutter run -d <device-id>
```

## Project structure

```
lib/
├── main.dart              # Entry point
├── app.dart               # Router + MaterialApp
├── core/
│   ├── api/               # API client + per-resource API classes
│   ├── models/            # Dart model classes (mirrors TypeScript types)
│   ├── services/          # Health Connect, etc.
│   └── theme/             # AppTheme + AppColors
├── providers/             # Riverpod state (auth, food, …)
├── screens/
│   ├── auth/              # Login + Register
│   ├── home/              # Dashboard (calories, macros, streak)
│   ├── log/               # Food log (AI text) + Workout log
│   ├── progress/          # Checkpoints + photos
│   ├── insights/          # Charts + AI patterns
│   └── profile/           # User stats + settings
└── widgets/               # Shared UI components
```

## Backend URL

Edit `lib/core/api/client.dart`:

| Environment | URL |
|---|---|
| Android emulator | `http://10.0.2.2:8000` (already set) |
| Physical device | `http://<your-LAN-IP>:8000` |
| Production | `https://api.your-domain.com` |

## Health Connect

Requires:
- Android 9+ device
- Google Health Connect app installed (comes pre-installed on Android 14+)
- Permissions granted on first launch

The sync flow:
1. `HealthConnectService.requestPermissions()` — prompts the user
2. `HealthConnectService.fetchToday()` → returns steps, calories, workouts
3. `HealthConnectApi.syncToday(...)` → posts to `POST /health-connect/sync`
4. Backend upserts into `daily_summaries` table, adjusting net calories

## Building for release

```powershell
# Generate signed APK (needs keystore — see Flutter docs)
flutter build apk --release

# Generate App Bundle for Play Store
flutter build appbundle --release
```
