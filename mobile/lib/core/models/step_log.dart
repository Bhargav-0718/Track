class StepLog {
  final String id;
  final DateTime date;
  final int steps;

  const StepLog({required this.id, required this.date, required this.steps});

  factory StepLog.fromJson(Map<String, dynamic> json) => StepLog(
        id: json['id'] as String,
        date: DateTime.parse(json['date'] as String),
        steps: json['steps'] as int,
      );
}
