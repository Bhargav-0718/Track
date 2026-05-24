import 'client.dart';

/// Sends Health Connect data collected on device to the backend
/// for integration into the daily dashboard and calorie tracking.
class HealthConnectApi {
  const HealthConnectApi._();

  /// POST /health-connect/sync
  /// Upserts steps + active minutes + calories burned into today's summary.
  static Future<void> syncToday({
    required String date, // YYYY-MM-DD
    required int steps,
    required int activeMinutes,
    required double activityCalories,
  }) async {
    await dio.post<void>(
      '/api/v1/health-connect/sync',
      data: {
        'date': date,
        'steps': steps,
        'active_minutes': activeMinutes,
        'activity_calories': activityCalories,
      },
    );
  }
}
