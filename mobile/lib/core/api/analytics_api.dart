import '../models/analytics.dart';
import 'client.dart';

class AnalyticsApi {
  const AnalyticsApi._();

  static Future<AnalyticsSummary> getSummary() async {
    final response = await dio.get<Map<String, dynamic>>('/api/v1/analytics/summary');
    return AnalyticsSummary.fromJson(response.data!);
  }

  static Future<TrendResponse> getTrends({int days = 30}) async {
    final response = await dio.get<Map<String, dynamic>>(
      '/api/v1/analytics/trends',
      queryParameters: {'days': days},
    );
    return TrendResponse.fromJson(response.data!);
  }

  static Future<StreakInfo> getStreak() async {
    final response = await dio.get<Map<String, dynamic>>('/api/v1/analytics/streak');
    return StreakInfo.fromJson(response.data!);
  }
}
