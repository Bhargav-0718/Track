import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../core/api/activity_api.dart';
import '../core/api/health_connect_api.dart';
import '../core/services/health_connect_service.dart';

// ── State model ───────────────────────────────────────────────────────────────

enum HcStatus {
  checking,
  unavailable,
  permissionDenied,
  ready,
  syncing,
  error,
}

class HealthConnectState {
  final HcStatus status;
  final HealthSummary? lastSummary;
  final DateTime? lastSyncedAt;
  final String? errorMessage;

  const HealthConnectState({
    this.status = HcStatus.checking,
    this.lastSummary,
    this.lastSyncedAt,
    this.errorMessage,
  });

  bool get hasSyncedToday {
    if (lastSyncedAt == null) return false;
    final now = DateTime.now();
    final s = lastSyncedAt!;
    return s.year == now.year && s.month == now.month && s.day == now.day;
  }

  HealthConnectState copyWith({
    HcStatus? status,
    HealthSummary? lastSummary,
    DateTime? lastSyncedAt,
    String? errorMessage,
  }) =>
      HealthConnectState(
        status: status ?? this.status,
        lastSummary: lastSummary ?? this.lastSummary,
        lastSyncedAt: lastSyncedAt ?? this.lastSyncedAt,
        errorMessage: errorMessage ?? this.errorMessage,
      );
}

// ── Notifier ──────────────────────────────────────────────────────────────────

class HealthConnectNotifier extends StateNotifier<HealthConnectState> {
  HealthConnectNotifier() : super(const HealthConnectState()) {
    _init();
  }

  Future<void> _init() async {
    try {
      final available = await HealthConnectService.isAvailable();
      if (!available) {
        state = state.copyWith(status: HcStatus.unavailable);
        return;
      }
      final granted = await _checkPermissions();
      state = state.copyWith(
        status: granted ? HcStatus.ready : HcStatus.permissionDenied,
      );
    } catch (e) {
      state = state.copyWith(status: HcStatus.error, errorMessage: e.toString());
    }
  }

  Future<bool> _checkPermissions() async {
    try {
      // Calling requestAuthorization with already-granted perms is a no-op on Android
      // and returns true — safe to call as a check.
      return await HealthConnectService.requestPermissions();
    } catch (_) {
      return false;
    }
  }

  /// Request Health Connect permissions. Call from a user gesture.
  Future<void> requestPermissions() async {
    state = state.copyWith(status: HcStatus.checking);
    final granted = await _checkPermissions();
    state = state.copyWith(
      status: granted ? HcStatus.ready : HcStatus.permissionDenied,
    );
  }

  /// Fetch today's data from Health Connect and push it to the backend.
  /// Also updates the step log so the activity chart reflects HC steps.
  Future<void> syncToday() async {
    if (state.status == HcStatus.unavailable) return;

    state = state.copyWith(status: HcStatus.syncing, errorMessage: null);

    try {
      // Ensure permissions are granted
      final granted = await _checkPermissions();
      if (!granted) {
        state = state.copyWith(status: HcStatus.permissionDenied);
        return;
      }

      final summary = await HealthConnectService.fetchToday();
      final today = DateFormat('yyyy-MM-dd').format(DateTime.now());

      // Push to Track backend
      await HealthConnectApi.syncToday(
        date: today,
        steps: summary.steps,
        activeMinutes: _estimateActiveMinutes(summary),
        activityCalories: summary.activeCaloriesBurned > 0
            ? summary.activeCaloriesBurned
            : summary.totalCaloriesBurned * 0.3, // fallback: ~30% of total
      );

      // Mirror steps into the manual step log so the 7-day chart stays accurate
      if (summary.steps > 0) {
        try {
          await ActivityApi.logSteps(steps: summary.steps);
        } catch (_) {
          // Non-fatal — step chart update is best-effort
        }
      }

      state = state.copyWith(
        status: HcStatus.ready,
        lastSummary: summary,
        lastSyncedAt: DateTime.now(),
      );
    } catch (e) {
      state = state.copyWith(
        status: HcStatus.error,
        errorMessage: e.toString(),
      );
    }
  }

  /// Estimate active minutes from workout records (fallback: steps / 100).
  int _estimateActiveMinutes(HealthSummary summary) {
    if (summary.workouts.isNotEmpty) {
      final totalSeconds =
          summary.workouts.fold(0, (s, w) => s + w.durationSeconds);
      return (totalSeconds / 60).round();
    }
    // Rough heuristic: ~1 active minute per 100 steps
    return (summary.steps / 100).round();
  }
}

// ── Provider ──────────────────────────────────────────────────────────────────

final healthConnectProvider =
    StateNotifierProvider<HealthConnectNotifier, HealthConnectState>(
  (ref) => HealthConnectNotifier(),
);
