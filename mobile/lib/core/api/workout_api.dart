import '../models/workout_log.dart';
import 'client.dart';

class WorkoutApi {
  const WorkoutApi._();

  static Future<List<WorkoutLog>> getRecent({int limit = 10}) async {
    // Backend uses page_size (not limit) for pagination
    final response = await dio.get<Map<String, dynamic>>(
      '/api/v1/workout-logs/',
      queryParameters: {'page_size': limit},
    );
    final items = (response.data!['items'] as List<dynamic>);
    return items.map((e) => WorkoutLog.fromJson(e as Map<String, dynamic>)).toList();
  }

  static Future<WorkoutLog> log({
    required String title,
    required WorkoutType workoutType,
    required int durationMinutes,
    required Intensity intensity,
    List<Exercise> exercises = const [],
    double? calories,
    String? notes,
    String? loggedAt,
  }) async {
    final response = await dio.post<Map<String, dynamic>>(
      '/api/v1/workout-logs/',
      data: {
        'title': title,
        'workout_type': workoutType.value,
        'duration_minutes': durationMinutes,
        'intensity': intensity.value,
        'exercises': exercises.map((e) => e.toJson()).toList(),
        if (calories != null) 'calories_burned': calories,
        if (notes != null) 'notes': notes,
        if (loggedAt != null) 'logged_at': loggedAt,
      },
    );
    return WorkoutLog.fromJson(response.data!);
  }

  static Future<void> delete(String id) async {
    await dio.delete('/api/v1/workout-logs/$id/');
  }

  static Future<Map<String, dynamic>> getDashboard() async {
    // Dashboard is at /dashboard, not /workout-logs/dashboard
    final response = await dio.get<Map<String, dynamic>>('/api/v1/dashboard');
    return response.data!;
  }
}
