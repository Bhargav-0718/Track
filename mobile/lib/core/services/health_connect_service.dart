import 'package:health/health.dart';

/// Service to read fitness data from Google Health Connect (Android)
/// and sync it to the Track backend.
///
/// Data flow:
///   Health Connect → HealthConnectService.syncToday() → WorkoutApi / food tracking
class HealthConnectService {
  static final _health = Health();

  /// Data types we request from Health Connect
  static const _types = [
    HealthDataType.STEPS,
    HealthDataType.ACTIVE_ENERGY_BURNED,
    HealthDataType.TOTAL_CALORIES_BURNED,
    HealthDataType.HEART_RATE,
    HealthDataType.WORKOUT,
    HealthDataType.WEIGHT,
    HealthDataType.HEIGHT,
  ];

  static const _permissions = [
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
  ];

  /// Request Health Connect permissions from the user.
  /// Returns true if all permissions were granted.
  static Future<bool> requestPermissions() async {
    await _health.configure();
    return _health.requestAuthorization(_types, permissions: _permissions);
  }

  /// Check if Health Connect is available on this device.
  static Future<bool> isAvailable() async {
    await _health.configure();
    return _health.isHealthConnectAvailable();
  }

  /// Fetch today's health data summary.
  static Future<HealthSummary> fetchToday() async {
    final now = DateTime.now();
    final startOfDay = DateTime(now.year, now.month, now.day);

    final data = await _health.getHealthDataFromTypes(
      types: _types,
      startTime: startOfDay,
      endTime: now,
    );

    return _aggregate(data);
  }

  /// Fetch health data for the past N days.
  static Future<List<DailyHealthData>> fetchLastDays(int days) async {
    final now = DateTime.now();
    final start = now.subtract(Duration(days: days));

    final data = await _health.getHealthDataFromTypes(
      types: _types,
      startTime: start,
      endTime: now,
    );

    // Group by day
    final Map<String, List<HealthDataPoint>> byDay = {};
    for (final point in data) {
      final key = '${point.dateFrom.year}-${point.dateFrom.month.toString().padLeft(2, '0')}-${point.dateFrom.day.toString().padLeft(2, '0')}';
      (byDay[key] ??= []).add(point);
    }

    return byDay.entries.map((e) {
      final summary = _aggregate(e.value);
      return DailyHealthData(date: e.key, summary: summary);
    }).toList()
      ..sort((a, b) => a.date.compareTo(b.date));
  }

  /// Aggregate raw Health Connect data points into a tidy summary.
  static HealthSummary _aggregate(List<HealthDataPoint> points) {
    int steps = 0;
    double activeCalories = 0;
    double totalCalories = 0;
    final List<HealthWorkout> workouts = [];

    for (final point in points) {
      switch (point.type) {
        case HealthDataType.STEPS:
          steps += (point.value as NumericHealthValue).numericValue.toInt();
        case HealthDataType.ACTIVE_ENERGY_BURNED:
          activeCalories += (point.value as NumericHealthValue).numericValue.toDouble();
        case HealthDataType.TOTAL_CALORIES_BURNED:
          totalCalories += (point.value as NumericHealthValue).numericValue.toDouble();
        case HealthDataType.WORKOUT:
          final wv = point.value as WorkoutHealthValue;
          workouts.add(HealthWorkout(
            type: wv.workoutActivityType.name,
            durationSeconds: point.dateTo.difference(point.dateFrom).inSeconds,
            calories: (wv.totalEnergyBurned ?? 0).toDouble(),
          ));
        default:
          break;
      }
    }

    return HealthSummary(
      steps: steps,
      activeCaloriesBurned: activeCalories,
      totalCaloriesBurned: totalCalories,
      workouts: workouts,
    );
  }
}

// ── Models ────────────────────────────────────────────────────────────────────

class HealthSummary {
  final int steps;
  final double activeCaloriesBurned;
  final double totalCaloriesBurned;
  final List<HealthWorkout> workouts;

  const HealthSummary({
    required this.steps,
    required this.activeCaloriesBurned,
    required this.totalCaloriesBurned,
    required this.workouts,
  });

  /// Estimated calories burned from steps (rough: ~0.04 kcal/step)
  double get stepCalories => steps * 0.04;

  Map<String, dynamic> toJson() => {
        'steps': steps,
        'active_calories_burned': activeCaloriesBurned,
        'total_calories_burned': totalCaloriesBurned,
        'workouts': workouts.map((w) => w.toJson()).toList(),
      };
}

class HealthWorkout {
  final String type;
  final int durationSeconds;
  final double calories;

  const HealthWorkout({
    required this.type,
    required this.durationSeconds,
    required this.calories,
  });

  Map<String, dynamic> toJson() => {
        'type': type,
        'duration_seconds': durationSeconds,
        'calories': calories,
      };
}

class DailyHealthData {
  final String date;
  final HealthSummary summary;
  const DailyHealthData({required this.date, required this.summary});
}
