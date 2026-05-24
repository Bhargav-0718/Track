class WorkoutLog {
  final String id;
  final String userId;
  final String title;
  final WorkoutType workoutType;
  final int durationMinutes;
  final Intensity intensity;
  final double? caloriesBurned;
  final List<Exercise> exercises;
  final String? notes;
  final DateTime loggedAt;

  const WorkoutLog({
    required this.id,
    required this.userId,
    required this.title,
    required this.workoutType,
    required this.durationMinutes,
    required this.intensity,
    this.caloriesBurned,
    required this.exercises,
    this.notes,
    required this.loggedAt,
  });

  factory WorkoutLog.fromJson(Map<String, dynamic> json) => WorkoutLog(
        id: json['id'] as String,
        userId: json['user_id'] as String,
        title: json['title'] as String,
        workoutType: WorkoutType.fromString(json['workout_type'] as String),
        durationMinutes: json['duration_minutes'] as int,
        intensity: Intensity.fromString(json['intensity'] as String),
        caloriesBurned: (json['calories_burned'] as num?)?.toDouble(),
        exercises: (json['exercises'] as List<dynamic>)
            .map((e) => Exercise.fromJson(e as Map<String, dynamic>))
            .toList(),
        notes: json['notes'] as String?,
        loggedAt: DateTime.parse(json['logged_at'] as String),
      );
}

class Exercise {
  final String name;
  final int? sets;
  final int? reps;
  final double? weightKg;
  final int? durationSeconds;

  const Exercise({
    required this.name,
    this.sets,
    this.reps,
    this.weightKg,
    this.durationSeconds,
  });

  factory Exercise.fromJson(Map<String, dynamic> json) => Exercise(
        name: json['name'] as String,
        sets: json['sets'] as int?,
        reps: json['reps'] as int?,
        weightKg: (json['weight_kg'] as num?)?.toDouble(),
        durationSeconds: json['duration_seconds'] as int?,
      );

  Map<String, dynamic> toJson() => {
        'name': name,
        if (sets != null) 'sets': sets,
        if (reps != null) 'reps': reps,
        if (weightKg != null) 'weight_kg': weightKg,
        if (durationSeconds != null) 'duration_seconds': durationSeconds,
      };
}

enum WorkoutType {
  strength('strength', 'Strength'),
  cardio('cardio', 'Cardio'),
  hiit('hiit', 'HIIT'),
  yoga('yoga', 'Yoga'),
  sports('sports', 'Sports'),
  other('other', 'Other');

  const WorkoutType(this.value, this.label);
  final String value;
  final String label;

  static WorkoutType fromString(String s) =>
      WorkoutType.values.firstWhere((e) => e.value == s, orElse: () => WorkoutType.other);
}

enum Intensity {
  low('low', 'Low'),
  moderate('moderate', 'Moderate'),
  high('high', 'High'),
  veryHigh('very_high', 'Very High');

  const Intensity(this.value, this.label);
  final String value;
  final String label;

  static Intensity fromString(String s) =>
      Intensity.values.firstWhere((e) => e.value == s, orElse: () => Intensity.moderate);
}
