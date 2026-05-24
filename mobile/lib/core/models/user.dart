// ignore_for_file: non_constant_identifier_names

class User {
  final String id;
  final String email;
  final String displayName;
  final String timezone;
  final int? age;
  final double? heightCm;
  final double? weightKg;
  final ActivityLevel activityLevel;
  final Goal goal;
  final int? targetCalories;
  final double? targetProteinG;
  final double? targetCarbsG;
  final double? targetFatG;
  final bool isActive;
  final DateTime createdAt;

  const User({
    required this.id,
    required this.email,
    required this.displayName,
    required this.timezone,
    this.age,
    this.heightCm,
    this.weightKg,
    required this.activityLevel,
    required this.goal,
    this.targetCalories,
    this.targetProteinG,
    this.targetCarbsG,
    this.targetFatG,
    required this.isActive,
    required this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> json) => User(
        id: json['id'] as String,
        email: json['email'] as String,
        displayName: json['display_name'] as String,
        timezone: json['timezone'] as String? ?? 'UTC',
        age: json['age'] as int?,
        heightCm: (json['height_cm'] as num?)?.toDouble(),
        weightKg: (json['weight_kg'] as num?)?.toDouble(),
        activityLevel: ActivityLevel.fromString(json['activity_level'] as String? ?? 'moderate'),
        goal: Goal.fromString(json['goal'] as String? ?? 'maintain'),
        targetCalories: json['target_calories'] as int?,
        targetProteinG: (json['target_protein_g'] as num?)?.toDouble(),
        targetCarbsG: (json['target_carbs_g'] as num?)?.toDouble(),
        targetFatG: (json['target_fat_g'] as num?)?.toDouble(),
        isActive: json['is_active'] as bool? ?? true,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'email': email,
        'display_name': displayName,
        'timezone': timezone,
        if (age != null) 'age': age,
        if (heightCm != null) 'height_cm': heightCm,
        if (weightKg != null) 'weight_kg': weightKg,
        'activity_level': activityLevel.value,
        'goal': goal.value,
        if (targetCalories != null) 'target_calories': targetCalories,
        if (targetProteinG != null) 'target_protein_g': targetProteinG,
        if (targetCarbsG != null) 'target_carbs_g': targetCarbsG,
        if (targetFatG != null) 'target_fat_g': targetFatG,
        'is_active': isActive,
        'created_at': createdAt.toIso8601String(),
      };

  User copyWith({
    String? displayName,
    int? age,
    double? heightCm,
    double? weightKg,
    ActivityLevel? activityLevel,
    Goal? goal,
    int? targetCalories,
    double? targetProteinG,
    double? targetCarbsG,
    double? targetFatG,
  }) =>
      User(
        id: id,
        email: email,
        displayName: displayName ?? this.displayName,
        timezone: timezone,
        age: age ?? this.age,
        heightCm: heightCm ?? this.heightCm,
        weightKg: weightKg ?? this.weightKg,
        activityLevel: activityLevel ?? this.activityLevel,
        goal: goal ?? this.goal,
        targetCalories: targetCalories ?? this.targetCalories,
        targetProteinG: targetProteinG ?? this.targetProteinG,
        targetCarbsG: targetCarbsG ?? this.targetCarbsG,
        targetFatG: targetFatG ?? this.targetFatG,
        isActive: isActive,
        createdAt: createdAt,
      );
}

enum ActivityLevel {
  sedentary('sedentary', 'Sedentary', 'Little or no exercise'),
  light('light', 'Lightly Active', '1–3 days/week'),
  moderate('moderate', 'Moderately Active', '3–5 days/week'),
  active('active', 'Very Active', '6–7 days/week'),
  veryActive('very_active', 'Extra Active', 'Physical job or 2x/day');

  const ActivityLevel(this.value, this.label, this.description);
  final String value;
  final String label;
  final String description;

  static ActivityLevel fromString(String s) =>
      ActivityLevel.values.firstWhere((e) => e.value == s, orElse: () => ActivityLevel.moderate);
}

enum Goal {
  loseWeight('lose_weight', 'Lose Weight', 'Calorie deficit'),
  maintain('maintain', 'Maintain', 'Stay at current weight'),
  gainMuscle('gain_muscle', 'Gain Muscle', 'Calorie surplus + protein'),
  improveFitness('improve_fitness', 'Improve Fitness', 'Performance focus');

  const Goal(this.value, this.label, this.description);
  final String value;
  final String label;
  final String description;

  static Goal fromString(String s) =>
      Goal.values.firstWhere((e) => e.value == s, orElse: () => Goal.maintain);
}
