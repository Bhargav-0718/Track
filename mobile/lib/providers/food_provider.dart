import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api/food_api.dart';
import '../core/models/food_log.dart';

// ── Today's food summary ──────────────────────────────────────────────────────

class TodayFoodNotifier extends StateNotifier<AsyncValue<DailyFoodSummary>> {
  TodayFoodNotifier() : super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final summary = await FoodApi.getToday();
      state = AsyncValue.data(summary);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<FoodLog> estimateAndLog({
    required String rawInput,
    required MealType mealType,
  }) async {
    final log = await FoodApi.estimateAndLog(rawInput: rawInput, mealType: mealType);
    await load(); // refresh totals
    return log;
  }

  Future<FoodLog> manualLog({
    required String foodName,
    required double calories,
    required MealType mealType,
    double? proteinG,
    double? carbsG,
    double? fatG,
    String? portionDescription,
  }) async {
    final log = await FoodApi.manualLog(
      foodName: foodName,
      calories: calories,
      mealType: mealType,
      proteinG: proteinG,
      carbsG: carbsG,
      fatG: fatG,
      portionDescription: portionDescription,
    );
    await load();
    return log;
  }

  Future<void> deleteLog(String id) async {
    await FoodApi.deleteLog(id);
    await load();
  }
}

final todayFoodProvider =
    StateNotifierProvider<TodayFoodNotifier, AsyncValue<DailyFoodSummary>>(
  (ref) => TodayFoodNotifier(),
);
