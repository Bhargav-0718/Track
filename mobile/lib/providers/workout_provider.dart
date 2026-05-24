import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api/workout_api.dart';
import '../core/models/workout_log.dart';

// ── Log screen tab (0 = Food, 1 = Workout) — shared so HomeScreen can set it ──

final logTabProvider = StateProvider<int>((ref) => 0);

// ── Exercise history — unique names from past 50 workouts ─────────────────────

final exerciseHistoryProvider = FutureProvider<List<String>>((ref) async {
  try {
    final logs = await WorkoutApi.getRecent(limit: 50);
    final names = <String>{};
    for (final log in logs) {
      for (final ex in log.exercises) {
        if (ex.name.trim().isNotEmpty) names.add(ex.name.trim());
      }
    }
    // Sort alphabetically for consistent autocomplete order
    return names.toList()..sort();
  } catch (_) {
    return [];
  }
});

// ── Recent workout logs ───────────────────────────────────────────────────────

class WorkoutLogsNotifier extends StateNotifier<AsyncValue<List<WorkoutLog>>> {
  WorkoutLogsNotifier() : super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final logs = await WorkoutApi.getRecent(limit: 20);
      state = AsyncValue.data(logs);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> addLog(WorkoutLog log) async {
    state.whenData((current) {
      state = AsyncValue.data([log, ...current]);
    });
  }
}

final workoutLogsProvider =
    StateNotifierProvider<WorkoutLogsNotifier, AsyncValue<List<WorkoutLog>>>(
  (ref) => WorkoutLogsNotifier(),
);
