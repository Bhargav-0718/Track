import '../models/step_log.dart';
import 'client.dart';

class ActivityApi {
  const ActivityApi._();

  /// Upsert today's step count. Pass [date] as 'YYYY-MM-DD' to log a past day.
  static Future<StepLog> logSteps({
    required int steps,
    String? date,
  }) async {
    final response = await dio.post<Map<String, dynamic>>(
      '/api/v1/activity/steps',
      data: {
        'steps': steps,
        if (date != null) 'date': date,
      },
    );
    return StepLog.fromJson(response.data!);
  }

  /// Get last [days] days of step history.
  static Future<List<StepLog>> getHistory({int days = 7}) async {
    final response = await dio.get<Map<String, dynamic>>(
      '/api/v1/activity/steps',
      queryParameters: {'days': days},
    );
    final items = response.data!['items'] as List<dynamic>;
    return items
        .map((e) => StepLog.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
