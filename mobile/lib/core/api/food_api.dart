import '../models/food_log.dart';
import 'client.dart';

class FoodApi {
  const FoodApi._();

  /// Get today's food logs with totals
  static Future<DailyFoodSummary> getToday() async {
    final today = DateTime.now();
    final dateStr = '${today.year}-${today.month.toString().padLeft(2, '0')}-${today.day.toString().padLeft(2, '0')}';
    return getByDate(dateStr);
  }

  static Future<DailyFoodSummary> getByDate(String date) async {
    final response = await dio.get<Map<String, dynamic>>(
      '/api/v1/food-logs/daily/$date',
    );
    return DailyFoodSummary.fromJson(response.data!);
  }

  /// AI-powered food estimation from text
  static Future<FoodLog> estimateAndLog({
    required String rawInput,
    required MealType mealType,
    String? loggedAt,
  }) async {
    final response = await dio.post<Map<String, dynamic>>(
      '/api/v1/food-logs/estimate',
      data: {
        'raw_input': rawInput,
        'meal_type': mealType.value,
        if (loggedAt != null) 'logged_at': loggedAt,
      },
    );
    return FoodLog.fromJson(response.data!);
  }

  /// Manual food log entry
  static Future<FoodLog> manualLog({
    required String foodName,
    required double calories,
    required MealType mealType,
    double? proteinG,
    double? carbsG,
    double? fatG,
    String? portionDescription,
    double? portionGrams,
    String? loggedAt,
  }) async {
    final response = await dio.post<Map<String, dynamic>>(
      '/api/v1/food-logs',
      data: {
        'food_name': foodName,
        'calories': calories,
        'meal_type': mealType.value,
        if (proteinG != null) 'protein_g': proteinG,
        if (carbsG != null) 'carbs_g': carbsG,
        if (fatG != null) 'fat_g': fatG,
        if (portionDescription != null) 'portion_description': portionDescription,
        if (portionGrams != null) 'portion_grams': portionGrams,
        if (loggedAt != null) 'logged_at': loggedAt,
      },
    );
    return FoodLog.fromJson(response.data!);
  }

  static Future<void> deleteLog(String id) async {
    await dio.delete('/api/v1/food-logs/$id');
  }

  static Future<FoodLog> correctLog(String id, Map<String, dynamic> data) async {
    final response = await dio.patch<Map<String, dynamic>>(
      '/api/v1/food-logs/$id/correct',
      data: data,
    );
    return FoodLog.fromJson(response.data!);
  }
}
