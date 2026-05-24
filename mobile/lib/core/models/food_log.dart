class FoodLog {
  final String id;
  final String userId;
  final String foodName;
  final String? brandName;
  final String? rawInput;
  final MealType mealType;
  final String? portionDescription;
  final double? portionGrams;
  final double calories;
  final double? proteinG;
  final double? carbsG;
  final double? fatG;
  final double? fiberG;
  final EstimationSource estimationSource;
  final double confidenceScore;
  final ConfidenceLevel confidenceLevel;
  final List<String> assumptions;
  final bool isCorrected;
  final DateTime loggedAt;
  final DateTime createdAt;

  const FoodLog({
    required this.id,
    required this.userId,
    required this.foodName,
    this.brandName,
    this.rawInput,
    required this.mealType,
    this.portionDescription,
    this.portionGrams,
    required this.calories,
    this.proteinG,
    this.carbsG,
    this.fatG,
    this.fiberG,
    required this.estimationSource,
    required this.confidenceScore,
    required this.confidenceLevel,
    required this.assumptions,
    required this.isCorrected,
    required this.loggedAt,
    required this.createdAt,
  });

  factory FoodLog.fromJson(Map<String, dynamic> json) => FoodLog(
        id: json['id'] as String,
        userId: json['user_id'] as String,
        foodName: json['food_name'] as String,
        brandName: json['brand_name'] as String?,
        rawInput: json['raw_input'] as String?,
        mealType: MealType.fromString(json['meal_type'] as String),
        portionDescription: json['portion_description'] as String?,
        portionGrams: (json['portion_grams'] as num?)?.toDouble(),
        calories: (json['calories'] as num).toDouble(),
        proteinG: (json['protein_g'] as num?)?.toDouble(),
        carbsG: (json['carbs_g'] as num?)?.toDouble(),
        fatG: (json['fat_g'] as num?)?.toDouble(),
        fiberG: (json['fiber_g'] as num?)?.toDouble(),
        estimationSource: EstimationSource.fromString(json['estimation_source'] as String),
        confidenceScore: (json['confidence_score'] as num).toDouble(),
        confidenceLevel: ConfidenceLevel.fromString(json['confidence_level'] as String),
        assumptions: (json['assumptions'] as List<dynamic>).cast<String>(),
        isCorrected: json['is_corrected'] as bool,
        loggedAt: DateTime.parse(json['logged_at'] as String),
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}

class DailyFoodSummary {
  final String date;
  final double totalCalories;
  final double totalProteinG;
  final double totalCarbsG;
  final double totalFatG;
  final int foodCount;
  final List<FoodLog> logs;

  const DailyFoodSummary({
    required this.date,
    required this.totalCalories,
    required this.totalProteinG,
    required this.totalCarbsG,
    required this.totalFatG,
    required this.foodCount,
    required this.logs,
  });

  factory DailyFoodSummary.fromJson(Map<String, dynamic> json) => DailyFoodSummary(
        date: json['date'] as String,
        totalCalories: (json['total_calories'] as num).toDouble(),
        totalProteinG: (json['total_protein_g'] as num).toDouble(),
        totalCarbsG: (json['total_carbs_g'] as num).toDouble(),
        totalFatG: (json['total_fat_g'] as num).toDouble(),
        foodCount: json['food_count'] as int,
        logs: (json['logs'] as List<dynamic>)
            .map((e) => FoodLog.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

enum MealType {
  breakfast('breakfast', 'Breakfast'),
  lunch('lunch', 'Lunch'),
  dinner('dinner', 'Dinner'),
  snack('snack', 'Snack'),
  preWorkout('pre_workout', 'Pre-Workout'),
  postWorkout('post_workout', 'Post-Workout');

  const MealType(this.value, this.label);
  final String value;
  final String label;

  static MealType fromString(String s) =>
      MealType.values.firstWhere((e) => e.value == s, orElse: () => MealType.snack);
}

enum EstimationSource {
  memory('memory'),
  dataset('dataset'),
  llm('llm'),
  manual('manual'),
  photo('photo'),
  healthConnect('health_connect');

  const EstimationSource(this.value);
  final String value;

  static EstimationSource fromString(String s) =>
      EstimationSource.values.firstWhere((e) => e.value == s, orElse: () => EstimationSource.llm);
}

enum ConfidenceLevel {
  confirmed('confirmed'),
  estimated('estimated'),
  uncertain('uncertain');

  const ConfidenceLevel(this.value);
  final String value;

  static ConfidenceLevel fromString(String s) =>
      ConfidenceLevel.values.firstWhere((e) => e.value == s, orElse: () => ConfidenceLevel.estimated);
}
