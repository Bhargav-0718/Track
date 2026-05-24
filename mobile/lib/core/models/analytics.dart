class StreakInfo {
  final int currentStreakDays;
  final int longestStreakDays;
  final String? streakStartedOn;
  final String? lastLoggedDate;
  final bool isActiveToday;

  const StreakInfo({
    required this.currentStreakDays,
    required this.longestStreakDays,
    this.streakStartedOn,
    this.lastLoggedDate,
    required this.isActiveToday,
  });

  factory StreakInfo.fromJson(Map<String, dynamic> json) => StreakInfo(
        currentStreakDays: json['current_streak_days'] as int,
        longestStreakDays: json['longest_streak_days'] as int,
        streakStartedOn: json['streak_started_on'] as String?,
        lastLoggedDate: json['last_logged_date'] as String?,
        isActiveToday: json['is_active_today'] as bool,
      );
}

class ConsistencyBreakdown {
  final double overallScore;
  final double loggingConsistency;
  final double calorieAdherence;
  final double proteinAdherence;
  final double workoutConsistency;
  final int periodDays;
  final String periodLabel;
  final int daysLogged;
  final int daysInPeriod;
  final int workoutsCompleted;

  const ConsistencyBreakdown({
    required this.overallScore,
    required this.loggingConsistency,
    required this.calorieAdherence,
    required this.proteinAdherence,
    required this.workoutConsistency,
    required this.periodDays,
    required this.periodLabel,
    required this.daysLogged,
    required this.daysInPeriod,
    required this.workoutsCompleted,
  });

  factory ConsistencyBreakdown.fromJson(Map<String, dynamic> json) => ConsistencyBreakdown(
        overallScore: (json['overall_score'] as num).toDouble(),
        loggingConsistency: (json['logging_consistency'] as num).toDouble(),
        calorieAdherence: (json['calorie_adherence'] as num).toDouble(),
        proteinAdherence: (json['protein_adherence'] as num).toDouble(),
        workoutConsistency: (json['workout_consistency'] as num).toDouble(),
        periodDays: json['period_days'] as int,
        periodLabel: json['period_label'] as String,
        daysLogged: json['days_logged'] as int,
        daysInPeriod: json['days_in_period'] as int,
        workoutsCompleted: json['workouts_completed'] as int,
      );
}

class DailyDataPoint {
  final String date;
  final double calories;
  final double? proteinG;
  final int workouts;
  final bool logged;
  final double? consistencyScore;

  const DailyDataPoint({
    required this.date,
    required this.calories,
    this.proteinG,
    required this.workouts,
    required this.logged,
    this.consistencyScore,
  });

  factory DailyDataPoint.fromJson(Map<String, dynamic> json) => DailyDataPoint(
        date: json['date'] as String,
        calories: (json['calories'] as num).toDouble(),
        proteinG: (json['protein_g'] as num?)?.toDouble(),
        workouts: json['workouts'] as int,
        logged: json['logged'] as bool,
        consistencyScore: (json['consistency_score'] as num?)?.toDouble(),
      );
}

class TrendResponse {
  final int periodDays;
  final List<DailyDataPoint> dataPoints;
  final double? calorieTarget;
  final double? proteinTargetG;
  final double averageCalories;
  final double? averageProteinG;

  const TrendResponse({
    required this.periodDays,
    required this.dataPoints,
    this.calorieTarget,
    this.proteinTargetG,
    required this.averageCalories,
    this.averageProteinG,
  });

  factory TrendResponse.fromJson(Map<String, dynamic> json) => TrendResponse(
        periodDays: json['period_days'] as int,
        dataPoints: (json['data_points'] as List<dynamic>)
            .map((e) => DailyDataPoint.fromJson(e as Map<String, dynamic>))
            .toList(),
        calorieTarget: (json['calorie_target'] as num?)?.toDouble(),
        proteinTargetG: (json['protein_target_g'] as num?)?.toDouble(),
        averageCalories: (json['average_calories'] as num).toDouble(),
        averageProteinG: (json['average_protein_g'] as num?)?.toDouble(),
      );
}

class AnalyticsSummary {
  final String userId;
  final StreakInfo streak;
  final ConsistencyBreakdown consistency7d;
  final ConsistencyBreakdown consistency30d;
  final List<String> patternInsights;
  final int checkpointsCount;
  final double? latestWeightKg;
  final double? weightTrendKg;
  final DateTime computedAt;

  const AnalyticsSummary({
    required this.userId,
    required this.streak,
    required this.consistency7d,
    required this.consistency30d,
    required this.patternInsights,
    required this.checkpointsCount,
    this.latestWeightKg,
    this.weightTrendKg,
    required this.computedAt,
  });

  factory AnalyticsSummary.fromJson(Map<String, dynamic> json) => AnalyticsSummary(
        userId: json['user_id'] as String,
        streak: StreakInfo.fromJson(json['streak'] as Map<String, dynamic>),
        consistency7d: ConsistencyBreakdown.fromJson(json['consistency_7d'] as Map<String, dynamic>),
        consistency30d: ConsistencyBreakdown.fromJson(json['consistency_30d'] as Map<String, dynamic>),
        patternInsights: (json['pattern_insights'] as List<dynamic>).cast<String>(),
        checkpointsCount: json['checkpoints_count'] as int,
        latestWeightKg: (json['latest_weight_kg'] as num?)?.toDouble(),
        weightTrendKg: (json['weight_trend_kg'] as num?)?.toDouble(),
        computedAt: DateTime.parse(json['computed_at'] as String),
      );
}
