import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/workout_api.dart';
import '../../core/models/food_log.dart';
import '../../core/models/workout_log.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/food_provider.dart';
import '../../providers/workout_provider.dart';

class LogScreen extends ConsumerWidget {
  const LogScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tab = ref.watch(logTabProvider);

    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.background,
        surfaceTintColor: Colors.transparent,
        title: const Text('Log', style: TextStyle(fontWeight: FontWeight.bold)),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(44),
          child: _TabBar(
            selected: tab,
            onChanged: (i) => ref.read(logTabProvider.notifier).state = i,
          ),
        ),
      ),
      body: tab == 0 ? const _FoodLogTab() : const _WorkoutLogTab(),
    );
  }
}

// ── Tab bar ───────────────────────────────────────────────────────────────────

class _TabBar extends StatelessWidget {
  const _TabBar({required this.selected, required this.onChanged});
  final int selected;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        child: Container(
          height: 36,
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: AppColors.border),
          ),
          child: Row(
            children: ['🍽  Food', '💪  Workout'].asMap().entries.map((entry) {
              final i = entry.key;
              final label = entry.value;
              final isSelected = i == selected;
              return Expanded(
                child: GestureDetector(
                  onTap: () => onChanged(i),
                  child: AnimatedContainer(
                    duration: 200.ms,
                    margin: const EdgeInsets.all(3),
                    decoration: BoxDecoration(
                      color: isSelected ? AppColors.emerald : Colors.transparent,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Center(
                      child: Text(
                        label,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                          color: isSelected ? Colors.white : AppColors.textMuted,
                        ),
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ),
      );
}

// ─────────────────────────────────────────────────────────────────────────────
// FOOD LOG TAB
// ─────────────────────────────────────────────────────────────────────────────

class _FoodLogTab extends ConsumerStatefulWidget {
  const _FoodLogTab();

  @override
  ConsumerState<_FoodLogTab> createState() => _FoodLogTabState();
}

class _FoodLogTabState extends ConsumerState<_FoodLogTab> {
  final _inputCtrl = TextEditingController();
  MealType _selectedMeal = MealType.lunch;
  bool _loading = false;
  String? _error;
  String? _lastResult;

  @override
  void dispose() {
    _inputCtrl.dispose();
    super.dispose();
  }

  Future<void> _estimate() async {
    if (_inputCtrl.text.trim().isEmpty) return;
    setState(() {
      _loading = true;
      _error = null;
      _lastResult = null;
    });
    try {
      final log = await ref.read(todayFoodProvider.notifier).estimateAndLog(
            rawInput: _inputCtrl.text.trim(),
            mealType: _selectedMeal,
          );
      setState(() {
        _lastResult = '${log.foodName} — ${log.calories.toInt()} kcal logged!';
        _inputCtrl.clear();
      });
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final foodAsync = ref.watch(todayFoodProvider);

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
      children: [
        // AI input card
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Log Food', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              const Text(
                'Describe what you ate — AI estimates nutrition automatically.',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
              const SizedBox(height: 16),

              // Meal type chips
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: MealType.values.map((mt) {
                    final selected = mt == _selectedMeal;
                    return GestureDetector(
                      onTap: () => setState(() => _selectedMeal = mt),
                      child: AnimatedContainer(
                        duration: 150.ms,
                        margin: const EdgeInsets.only(right: 8),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: selected ? AppColors.emerald : AppColors.surfaceElevated,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: selected ? AppColors.emerald : AppColors.border,
                          ),
                        ),
                        child: Text(
                          mt.label,
                          style: TextStyle(
                            fontSize: 12,
                            color: selected ? Colors.white : AppColors.textSecondary,
                            fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 12),

              TextField(
                controller: _inputCtrl,
                maxLines: 3,
                decoration: const InputDecoration(
                  hintText: 'e.g. "2 rotis with dal and sabzi" or "protein shake 30g"',
                  alignLabelWithHint: true,
                ),
              ),
              const SizedBox(height: 12),

              if (_lastResult != null)
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.emerald.withAlpha(26),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.check_circle_outline, color: AppColors.emerald, size: 16),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(_lastResult!,
                            style: const TextStyle(color: AppColors.emerald, fontSize: 13)),
                      ),
                    ],
                  ),
                ).animate().fadeIn(duration: 300.ms),

              if (_error != null)
                Text(_error!, style: const TextStyle(color: AppColors.red, fontSize: 13))
                    .animate()
                    .fadeIn(duration: 200.ms),

              const SizedBox(height: 12),

              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _loading ? null : _estimate,
                  icon: _loading
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.auto_awesome_rounded, size: 16),
                  label: Text(_loading ? 'Estimating...' : 'Estimate & Log'),
                ),
              ),
            ],
          ),
        ).animate().fadeIn(duration: 400.ms),
        const SizedBox(height: 20),

        // Today's logs
        const Text("Today's Entries",
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
        const SizedBox(height: 10),

        foodAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) =>
              Text(e.toString(), style: const TextStyle(color: AppColors.red)),
          data: (summary) => summary.logs.isEmpty
              ? const Center(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Text('No entries yet.',
                        style: TextStyle(color: AppColors.textMuted)),
                  ),
                )
              : Column(
                  children: summary.logs.asMap().entries.map((entry) {
                    final i = entry.key;
                    final log = entry.value;
                    return Dismissible(
                      key: Key(log.id),
                      direction: DismissDirection.endToStart,
                      background: Container(
                        alignment: Alignment.centerRight,
                        padding: const EdgeInsets.only(right: 16),
                        decoration: BoxDecoration(
                          color: AppColors.red.withAlpha(51),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.delete_outline, color: AppColors.red),
                      ),
                      onDismissed: (_) =>
                          ref.read(todayFoodProvider.notifier).deleteLog(log.id),
                      child: Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(log.foodName,
                                      style: const TextStyle(fontWeight: FontWeight.w500)),
                                  const SizedBox(height: 2),
                                  Row(
                                    children: [
                                      _ConfidenceDot(level: log.confidenceLevel.value),
                                      const SizedBox(width: 6),
                                      Text(log.mealType.label,
                                          style: const TextStyle(
                                              color: AppColors.textMuted, fontSize: 12)),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                Text('${log.calories.toInt()} kcal',
                                    style: const TextStyle(
                                        fontWeight: FontWeight.bold, fontSize: 14)),
                                if (log.proteinG != null)
                                  Text('P: ${log.proteinG!.toInt()}g',
                                      style: const TextStyle(
                                          color: AppColors.textMuted, fontSize: 12)),
                              ],
                            ),
                          ],
                        ),
                      ).animate().fadeIn(delay: (i * 50).ms, duration: 300.ms),
                    );
                  }).toList(),
                ),
        ),
      ],
    );
  }
}

class _ConfidenceDot extends StatelessWidget {
  const _ConfidenceDot({required this.level});
  final String level;

  @override
  Widget build(BuildContext context) {
    final color = switch (level) {
      'confirmed' => AppColors.emerald,
      'estimated' => AppColors.amber,
      _ => AppColors.textMuted,
    };
    return Container(
      width: 6,
      height: 6,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// WORKOUT LOG TAB — simplified: exercises + total calories from your app
// ─────────────────────────────────────────────────────────────────────────────

/// One row in the exercise list
class _ExEntry {
  final TextEditingController nameCtrl;
  final TextEditingController setsCtrl;
  final TextEditingController repsCtrl;

  _ExEntry()
      : nameCtrl = TextEditingController(),
        setsCtrl = TextEditingController(),
        repsCtrl = TextEditingController();

  void dispose() {
    nameCtrl.dispose();
    setsCtrl.dispose();
    repsCtrl.dispose();
  }

  bool get hasName => nameCtrl.text.trim().isNotEmpty;

  Exercise toExercise() => Exercise(
        name: nameCtrl.text.trim(),
        sets: int.tryParse(setsCtrl.text),
        reps: int.tryParse(repsCtrl.text),
      );
}

class _WorkoutLogTab extends ConsumerStatefulWidget {
  const _WorkoutLogTab();

  @override
  ConsumerState<_WorkoutLogTab> createState() => _WorkoutLogTabState();
}

class _WorkoutLogTabState extends ConsumerState<_WorkoutLogTab> {
  final _titleCtrl = TextEditingController();
  final _caloriesCtrl = TextEditingController();
  final _durationCtrl = TextEditingController();
  final List<_ExEntry> _exercises = [_ExEntry()]; // start with one row
  WorkoutType _type = WorkoutType.strength;
  bool _loading = false;
  String? _success;

  @override
  void dispose() {
    _titleCtrl.dispose();
    _caloriesCtrl.dispose();
    _durationCtrl.dispose();
    for (final e in _exercises) {
      e.dispose();
    }
    super.dispose();
  }

  void _addExercise() {
    setState(() => _exercises.add(_ExEntry()));
  }

  void _removeExercise(int i) {
    if (_exercises.length == 1) return; // keep at least one
    setState(() {
      _exercises[i].dispose();
      _exercises.removeAt(i);
    });
  }

  Future<void> _log() async {
    final validExercises = _exercises.where((e) => e.hasName).toList();
    if (validExercises.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Add at least one exercise')),
      );
      return;
    }

    setState(() {
      _loading = true;
      _success = null;
    });

    try {
      final title = _titleCtrl.text.trim().isEmpty
          ? validExercises.map((e) => e.nameCtrl.text.trim()).join(', ')
          : _titleCtrl.text.trim();

      final calories = double.tryParse(_caloriesCtrl.text);
      final duration = int.tryParse(_durationCtrl.text) ?? 30;

      final w = await WorkoutApi.log(
        title: title,
        workoutType: _type,
        durationMinutes: duration,
        intensity: Intensity.moderate,
        calories: calories,
        exercises: validExercises.map((e) => e.toExercise()).toList(),
      );

      // Refresh exercise history so new exercises appear in autocomplete
      ref.invalidate(exerciseHistoryProvider);
      ref.read(workoutLogsProvider.notifier).addLog(w);

      setState(() {
        _success = '${w.title} logged! ${calories != null ? '${calories.toInt()} kcal' : ''}';
        _titleCtrl.clear();
        _caloriesCtrl.clear();
        _durationCtrl.clear();
        for (final e in _exercises) {
          e.dispose();
        }
        _exercises
          ..clear()
          ..add(_ExEntry());
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final historyAsync = ref.watch(exerciseHistoryProvider);
    final exerciseNames = historyAsync.value ?? [];

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
      children: [
        // ── Main card ──────────────────────────────────────────────────────
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(7),
                    decoration: BoxDecoration(
                      color: AppColors.blue.withAlpha(30),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.fitness_center_rounded,
                        color: AppColors.blue, size: 18),
                  ),
                  const SizedBox(width: 10),
                  const Text('Log Workout',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                ],
              ),
              const SizedBox(height: 16),

              // ── Workout type chips ─────────────────────────────────────
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: WorkoutType.values.map((t) {
                    final sel = t == _type;
                    return GestureDetector(
                      onTap: () => setState(() => _type = t),
                      child: AnimatedContainer(
                        duration: 150.ms,
                        margin: const EdgeInsets.only(right: 8),
                        padding:
                            const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: sel
                              ? AppColors.blue.withAlpha(50)
                              : AppColors.surfaceElevated,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                              color: sel ? AppColors.blue : AppColors.border),
                        ),
                        child: Text(
                          t.label,
                          style: TextStyle(
                            fontSize: 12,
                            color: sel ? AppColors.blue : AppColors.textSecondary,
                            fontWeight:
                                sel ? FontWeight.w600 : FontWeight.normal,
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 16),

              // ── Optional title + duration row ──────────────────────────
              Row(
                children: [
                  Expanded(
                    flex: 3,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _fieldLabel('Session name (optional)'),
                        const SizedBox(height: 6),
                        TextField(
                          controller: _titleCtrl,
                          decoration: const InputDecoration(
                            hintText: 'e.g. Push day',
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    flex: 2,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _fieldLabel('Duration (min)'),
                        const SizedBox(height: 6),
                        TextField(
                          controller: _durationCtrl,
                          keyboardType: TextInputType.number,
                          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                          decoration: const InputDecoration(hintText: '45'),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // ── Exercises header ───────────────────────────────────────
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _fieldLabel('Exercises'),
                  if (exerciseNames.isNotEmpty)
                    Text(
                      '${exerciseNames.length} saved',
                      style: const TextStyle(
                          color: AppColors.textMuted, fontSize: 12),
                    ),
                ],
              ),
              const SizedBox(height: 8),

              // Column header labels
              const Padding(
                padding: EdgeInsets.only(left: 4, bottom: 6),
                child: Row(
                  children: [
                    Expanded(
                      flex: 5,
                      child: Text('Exercise',
                          style:
                              TextStyle(color: AppColors.textMuted, fontSize: 11)),
                    ),
                    SizedBox(width: 8),
                    SizedBox(
                      width: 44,
                      child: Text('Sets',
                          textAlign: TextAlign.center,
                          style:
                              TextStyle(color: AppColors.textMuted, fontSize: 11)),
                    ),
                    SizedBox(width: 8),
                    SizedBox(
                      width: 44,
                      child: Text('Reps',
                          textAlign: TextAlign.center,
                          style:
                              TextStyle(color: AppColors.textMuted, fontSize: 11)),
                    ),
                    SizedBox(width: 32), // space for delete icon
                  ],
                ),
              ),

              // ── Exercise rows ──────────────────────────────────────────
              ..._exercises.asMap().entries.map((entry) {
                final i = entry.key;
                final ex = entry.value;
                return _ExerciseRow(
                  key: ObjectKey(ex),
                  entry: ex,
                  history: exerciseNames,
                  onRemove: _exercises.length > 1 ? () => _removeExercise(i) : null,
                );
              }),

              // Add exercise button
              TextButton.icon(
                onPressed: _addExercise,
                icon: const Icon(Icons.add_rounded, size: 18, color: AppColors.blue),
                label: const Text('Add exercise',
                    style: TextStyle(color: AppColors.blue, fontSize: 13)),
                style: TextButton.styleFrom(padding: EdgeInsets.zero),
              ),
              const SizedBox(height: 16),

              // ── Calories field ─────────────────────────────────────────
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.surfaceElevated,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.border),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.local_fire_department_rounded,
                        color: AppColors.amber, size: 22),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Calories burned',
                            style: TextStyle(
                                color: AppColors.textSecondary, fontSize: 12),
                          ),
                          const SizedBox(height: 4),
                          TextField(
                            controller: _caloriesCtrl,
                            keyboardType: TextInputType.number,
                            inputFormatters: [
                              FilteringTextInputFormatter.digitsOnly
                            ],
                            decoration: const InputDecoration(
                              hintText: '450',
                              suffixText: 'kcal',
                              border: InputBorder.none,
                              enabledBorder: InputBorder.none,
                              focusedBorder: InputBorder.none,
                              contentPadding: EdgeInsets.zero,
                              isDense: true,
                            ),
                            style: const TextStyle(
                                fontSize: 22, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                    ),
                    const Text(
                      'from\nyour app',
                      textAlign: TextAlign.right,
                      style: TextStyle(
                          color: AppColors.textMuted, fontSize: 11, height: 1.3),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Success banner
              if (_success != null)
                Container(
                  padding: const EdgeInsets.all(10),
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    color: AppColors.emerald.withAlpha(26),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.check_circle_outline,
                          color: AppColors.emerald, size: 16),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(_success!,
                            style: const TextStyle(
                                color: AppColors.emerald, fontSize: 13)),
                      ),
                    ],
                  ),
                ).animate().fadeIn(duration: 300.ms),

              // Log button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _loading ? null : _log,
                  style:
                      ElevatedButton.styleFrom(backgroundColor: AppColors.blue),
                  icon: _loading
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.fitness_center_rounded, size: 16),
                  label: Text(_loading ? 'Logging...' : 'Log Workout'),
                ),
              ),
            ],
          ),
        ).animate().fadeIn(duration: 400.ms),

        // ── Recent workouts ────────────────────────────────────────────────
        const SizedBox(height: 24),
        const Text('Recent Workouts',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
        const SizedBox(height: 10),
        _RecentWorkouts(),
      ],
    );
  }

  Widget _fieldLabel(String text) => Text(
        text,
        style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
      );
}

// ── Exercise row with autocomplete ────────────────────────────────────────────

class _ExerciseRow extends StatefulWidget {
  const _ExerciseRow({
    super.key,
    required this.entry,
    required this.history,
    this.onRemove,
  });

  final _ExEntry entry;
  final List<String> history;
  final VoidCallback? onRemove;

  @override
  State<_ExerciseRow> createState() => _ExerciseRowState();
}

class _ExerciseRowState extends State<_ExerciseRow> {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Exercise name with autocomplete
          Expanded(
            flex: 5,
            child: _ExerciseAutocomplete(
              controller: widget.entry.nameCtrl,
              history: widget.history,
            ),
          ),
          const SizedBox(width: 8),

          // Sets
          SizedBox(
            width: 44,
            child: TextField(
              controller: widget.entry.setsCtrl,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              textAlign: TextAlign.center,
              decoration: const InputDecoration(
                hintText: '3',
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 6, vertical: 12),
              ),
            ),
          ),
          const SizedBox(width: 8),

          // Reps
          SizedBox(
            width: 44,
            child: TextField(
              controller: widget.entry.repsCtrl,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              textAlign: TextAlign.center,
              decoration: const InputDecoration(
                hintText: '10',
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 6, vertical: 12),
              ),
            ),
          ),

          // Delete button
          SizedBox(
            width: 32,
            child: widget.onRemove != null
                ? IconButton(
                    padding: EdgeInsets.zero,
                    icon: const Icon(Icons.close_rounded,
                        size: 18, color: AppColors.textMuted),
                    onPressed: widget.onRemove,
                  )
                : const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }
}

// ── Autocomplete widget for exercise names ────────────────────────────────────

class _ExerciseAutocomplete extends StatelessWidget {
  const _ExerciseAutocomplete({
    required this.controller,
    required this.history,
  });

  final TextEditingController controller;
  final List<String> history;

  @override
  Widget build(BuildContext context) {
    return RawAutocomplete<String>(
      textEditingController: controller,
      focusNode: FocusNode(),
      optionsBuilder: (textEditingValue) {
        if (textEditingValue.text.isEmpty) return const [];
        final query = textEditingValue.text.toLowerCase();
        return history.where((name) => name.toLowerCase().contains(query));
      },
      displayStringForOption: (option) => option,
      fieldViewBuilder: (context, ctrl, focusNode, onSubmit) => TextField(
        controller: ctrl,
        focusNode: focusNode,
        textCapitalization: TextCapitalization.words,
        decoration: const InputDecoration(hintText: 'Exercise name'),
        onEditingComplete: onSubmit,
      ),
      optionsViewBuilder: (context, onSelected, options) => Align(
        alignment: Alignment.topLeft,
        child: Material(
          color: AppColors.surfaceElevated,
          borderRadius: BorderRadius.circular(10),
          elevation: 4,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 200, maxWidth: 240),
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 4),
              shrinkWrap: true,
              itemCount: options.length,
              itemBuilder: (context, i) {
                final option = options.elementAt(i);
                return InkWell(
                  onTap: () => onSelected(option),
                  child: Padding(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    child: Row(
                      children: [
                        const Icon(Icons.history_rounded,
                            size: 14, color: AppColors.textMuted),
                        const SizedBox(width: 8),
                        Text(option,
                            style: const TextStyle(
                                fontSize: 14, color: AppColors.textPrimary)),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}

// ── Recent workouts list ──────────────────────────────────────────────────────

class _RecentWorkouts extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final logsAsync = ref.watch(workoutLogsProvider);

    return logsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => const SizedBox.shrink(),
      data: (logs) => logs.isEmpty
          ? const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('No workouts yet.',
                    style: TextStyle(color: AppColors.textMuted)),
              ),
            )
          : Column(
              children: logs.asMap().entries.map((entry) {
                final i = entry.key;
                final log = entry.value;
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(
                          color: AppColors.blue.withAlpha(26),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Icon(Icons.fitness_center_rounded,
                            color: AppColors.blue, size: 20),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(log.title,
                                style: const TextStyle(
                                    fontWeight: FontWeight.w500, fontSize: 14)),
                            Text(
                              '${log.workoutType.label} · ${log.durationMinutes} min'
                              '${log.exercises.isNotEmpty ? ' · ${log.exercises.length} exercises' : ''}',
                              style: const TextStyle(
                                  color: AppColors.textMuted, fontSize: 12),
                            ),
                          ],
                        ),
                      ),
                      if (log.caloriesBurned != null)
                        Text(
                          '${log.caloriesBurned!.toInt()} kcal',
                          style: const TextStyle(
                              fontWeight: FontWeight.w600,
                              fontSize: 14,
                              color: AppColors.amber),
                        ),
                    ],
                  ),
                ).animate().fadeIn(delay: (i * 40).ms, duration: 300.ms);
              }).toList(),
            ),
    );
  }
}
