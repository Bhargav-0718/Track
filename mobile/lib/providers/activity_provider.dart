import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api/activity_api.dart';
import '../core/models/step_log.dart';

// ── Step history (last 7 days) ────────────────────────────────────────────────

class StepHistoryNotifier extends StateNotifier<AsyncValue<List<StepLog>>> {
  StepHistoryNotifier() : super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final logs = await ActivityApi.getHistory(days: 7);
      state = AsyncValue.data(logs);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<StepLog> logSteps(int steps) async {
    final log = await ActivityApi.logSteps(steps: steps);
    // Re-fetch to keep history in sync
    await load();
    return log;
  }
}

final stepHistoryProvider =
    StateNotifierProvider<StepHistoryNotifier, AsyncValue<List<StepLog>>>(
  (ref) => StepHistoryNotifier(),
);

// ── BMR + step calorie helpers (pure functions, no network) ───────────────────

/// Mifflin-St Jeor BMR (kcal/day).
/// gender: 'male', 'female', or anything else treated as average.
double calculateBmr({
  required double weightKg,
  required double heightCm,
  required int age,
  required String gender,
}) {
  final base = 10 * weightKg + 6.25 * heightCm - 5 * age;
  if (gender == 'male') return base + 5;
  if (gender == 'female') return base - 161;
  return base - 78; // midpoint for 'other'
}

/// Approximate distance in km from step count.
double stepsToKm({required int steps, required double heightCm}) {
  final strideLengthM = heightCm * 0.415 / 100; // metres
  return steps * strideLengthM / 1000;
}

/// Approximate active calories burned from walking.
double stepsToCalories({
  required int steps,
  required double weightKg,
  required double heightCm,
}) {
  final distanceKm = stepsToKm(steps: steps, heightCm: heightCm);
  return distanceKm * weightKg * 1.036;
}
