import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/workout_api.dart';
import '../../core/models/food_log.dart';
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
// FOOD LOG TAB — with compound meal grouping
// ─────────────────────────────────────────────────────────────────────────────

/// Groups food logs by meal_group_id. Singles (no group) each form their own group.
class _MealGroup {
  final String id;
  final MealType mealType;
  final List<FoodLog> logs;

  _MealGroup({required this.id, required this.mealType, required this.logs});

  double get totalCalories => logs.fold(0, (s, l) => s + l.calories);
  double? get totalProtein {
    if (logs.every((l) => l.proteinG == null)) return null;
    return logs.fold<double>(0.0, (s, l) => s + (l.proteinG ?? 0));
  }

  String get headerName => logs.map((l) => l.foodName).join(' · ');
  bool get isCompound => logs.length > 1;
}

List<_MealGroup> _buildMealGroups(List<FoodLog> logs) {
  final Map<String, _MealGroup> grouped = {};
  final List<_MealGroup> result = [];

  for (final log in logs) {
    final gid = log.mealGroupId;
    if (gid != null) {
      if (grouped.containsKey(gid)) {
        grouped[gid]!.logs.add(log);
      } else {
        final g = _MealGroup(id: gid, mealType: log.mealType, logs: [log]);
        grouped[gid] = g;
        result.add(g);
      }
    } else {
      result.add(_MealGroup(id: log.id, mealType: log.mealType, logs: [log]));
    }
  }
  return result;
}

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
      final logs = await ref.read(todayFoodProvider.notifier).estimateAndLog(
            rawInput: _inputCtrl.text.trim(),
            mealType: _selectedMeal,
          );
      final totalKcal = logs.fold(0.0, (s, l) => s + l.calories).toInt();
      final names = logs.map((l) => l.foodName).join(', ');
      setState(() {
        _lastResult = logs.length == 1
            ? '${logs.first.foodName} — $totalKcal kcal logged!'
            : '$names — $totalKcal kcal total (${logs.length} items)';
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
        // ── AI input card ────────────────────────────────────────────────────
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
              const Text('Log Food',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              const Text(
                'Describe what you ate — AI estimates nutrition and splits compound meals.',
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
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: selected
                              ? AppColors.emerald
                              : AppColors.surfaceElevated,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: selected
                                ? AppColors.emerald
                                : AppColors.border,
                          ),
                        ),
                        child: Text(
                          mt.label,
                          style: TextStyle(
                            fontSize: 12,
                            color: selected
                                ? Colors.white
                                : AppColors.textSecondary,
                            fontWeight: selected
                                ? FontWeight.w600
                                : FontWeight.normal,
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
                  hintText:
                      'e.g. "3 roti with bhindi sabji and kadhi" or "protein shake 30g"',
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
                      const Icon(Icons.check_circle_outline,
                          color: AppColors.emerald, size: 16),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(_lastResult!,
                            style: const TextStyle(
                                color: AppColors.emerald, fontSize: 13)),
                      ),
                    ],
                  ),
                ).animate().fadeIn(duration: 300.ms),

              if (_error != null)
                Text(_error!,
                        style:
                            const TextStyle(color: AppColors.red, fontSize: 13))
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
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.auto_awesome_rounded, size: 16),
                  label:
                      Text(_loading ? 'Estimating...' : 'Estimate & Log'),
                ),
              ),
            ],
          ),
        ).animate().fadeIn(duration: 400.ms),
        const SizedBox(height: 20),

        // ── Today's entries ──────────────────────────────────────────────────
        const Text("Today's Entries",
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
        const SizedBox(height: 10),

        foodAsync.when(
          loading: () =>
              const Center(child: CircularProgressIndicator()),
          error: (e, _) => Text(e.toString(),
              style: const TextStyle(color: AppColors.red)),
          data: (summary) {
            final groups = _buildMealGroups(summary.logs);
            if (groups.isEmpty) {
              return const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: Text('No entries yet.',
                      style: TextStyle(color: AppColors.textMuted)),
                ),
              );
            }
            return Column(
              children: groups.asMap().entries.map((entry) {
                final i = entry.key;
                final group = entry.value;
                return group.isCompound
                    ? _CompoundMealCard(
                        group: group,
                        onDelete: (id) => ref
                            .read(todayFoodProvider.notifier)
                            .deleteLog(id),
                      ).animate().fadeIn(
                            delay: (i * 50).ms, duration: 300.ms)
                    : _SingleFoodCard(
                        log: group.logs.first,
                        onDelete: () => ref
                            .read(todayFoodProvider.notifier)
                            .deleteLog(group.logs.first.id),
                      ).animate().fadeIn(
                            delay: (i * 50).ms, duration: 300.ms);
              }).toList(),
            );
          },
        ),
      ],
    );
  }
}

// ── Single food card ───────────────────────────────────────────────────────────

class _SingleFoodCard extends StatelessWidget {
  const _SingleFoodCard({required this.log, required this.onDelete});
  final FoodLog log;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) => Dismissible(
        key: Key(log.id),
        direction: DismissDirection.endToStart,
        background: _DeleteBg(),
        onDismissed: (_) => onDelete(),
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
                        style:
                            const TextStyle(fontWeight: FontWeight.w500)),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        _ConfidenceDot(level: log.confidenceLevel.value),
                        const SizedBox(width: 6),
                        Text(log.mealType.label,
                            style: const TextStyle(
                                color: AppColors.textMuted, fontSize: 12)),
                        if (log.quantity > 1) ...[
                          const SizedBox(width: 6),
                          Text('× ${log.quantity % 1 == 0 ? log.quantity.toInt() : log.quantity}',
                              style: const TextStyle(
                                  color: AppColors.textMuted, fontSize: 12)),
                        ],
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
                  if (log.caloriesPerUnit != null && log.quantity > 1)
                    Text(
                        '${log.caloriesPerUnit!.toInt()} kcal/unit',
                        style: const TextStyle(
                            color: AppColors.textMuted, fontSize: 11)),
                  if (log.proteinG != null)
                    Text('P: ${log.proteinG!.toInt()}g',
                        style: const TextStyle(
                            color: AppColors.textMuted, fontSize: 12)),
                ],
              ),
            ],
          ),
        ),
      );
}

// ── Compound meal card ─────────────────────────────────────────────────────────

class _CompoundMealCard extends StatefulWidget {
  const _CompoundMealCard({required this.group, required this.onDelete});
  final _MealGroup group;
  final void Function(String id) onDelete;

  @override
  State<_CompoundMealCard> createState() => _CompoundMealCardState();
}

class _CompoundMealCardState extends State<_CompoundMealCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final group = widget.group;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          // Header row — tap to expand
          InkWell(
            onTap: () => setState(() => _expanded = !_expanded),
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          group.headerName,
                          style: const TextStyle(
                              fontWeight: FontWeight.w500, fontSize: 14),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${group.mealType.label} · ${group.logs.length} items',
                          style: const TextStyle(
                              color: AppColors.textMuted, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  Text(
                    '${group.totalCalories.toInt()} kcal',
                    style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color: AppColors.amber),
                  ),
                  const SizedBox(width: 8),
                  Icon(
                    _expanded
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    color: AppColors.textMuted,
                    size: 20,
                  ),
                ],
              ),
            ),
          ),

          // Expanded components
          if (_expanded) ...[
            const Divider(height: 1, color: AppColors.border),
            ...group.logs.map((log) => _ComponentRow(
                  log: log,
                  onDelete: () => widget.onDelete(log.id),
                )),
            // Macro totals
            if (group.totalProtein != null)
              Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text('Protein: ${group.totalProtein!.toInt()}g',
                        style: const TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 12,
                            fontStyle: FontStyle.italic)),
                  ],
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _ComponentRow extends StatelessWidget {
  const _ComponentRow({required this.log, required this.onDelete});
  final FoodLog log;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          children: [
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(log.foodName,
                          style: const TextStyle(fontSize: 13)),
                      if (log.quantity > 1) ...[
                        const SizedBox(width: 4),
                        Text(
                          '× ${log.quantity % 1 == 0 ? log.quantity.toInt() : log.quantity}',
                          style: const TextStyle(
                              color: AppColors.textMuted, fontSize: 12),
                        ),
                      ],
                    ],
                  ),
                  if (log.caloriesPerUnit != null && log.quantity > 1)
                    Text(
                      '${log.caloriesPerUnit!.toInt()} kcal/unit',
                      style: const TextStyle(
                          color: AppColors.textMuted, fontSize: 11),
                    ),
                ],
              ),
            ),
            Text('${log.calories.toInt()} kcal',
                style: const TextStyle(
                    fontWeight: FontWeight.w500, fontSize: 13)),
            const SizedBox(width: 4),
            IconButton(
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
              icon: const Icon(Icons.close_rounded,
                  size: 16, color: AppColors.textMuted),
              onPressed: onDelete,
            ),
          ],
        ),
      );
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

class _DeleteBg extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 16),
        decoration: BoxDecoration(
          color: AppColors.red.withAlpha(51),
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Icon(Icons.delete_outline, color: AppColors.red),
      );
}

// ─────────────────────────────────────────────────────────────────────────────
// WORKOUT LOG TAB — 3 sections: App Workout / Cardio / Strength
// ─────────────────────────────────────────────────────────────────────────────

enum _WorkoutSection { appWorkout, cardio, strength }

class _WorkoutLogTab extends ConsumerStatefulWidget {
  const _WorkoutLogTab();

  @override
  ConsumerState<_WorkoutLogTab> createState() => _WorkoutLogTabState();
}

class _WorkoutLogTabState extends ConsumerState<_WorkoutLogTab> {
  _WorkoutSection _section = _WorkoutSection.appWorkout;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
      children: [
        // ── Section selector ─────────────────────────────────────────────────
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.border),
          ),
          child: Column(
            children: [
              // 3 tab buttons
              Row(
                children: [
                  _SectionTab(
                    icon: Icons.smartphone_rounded,
                    label: 'App',
                    active: _section == _WorkoutSection.appWorkout,
                    onTap: () =>
                        setState(() => _section = _WorkoutSection.appWorkout),
                  ),
                  const SizedBox(width: 8),
                  _SectionTab(
                    icon: Icons.directions_bike_rounded,
                    label: 'Cardio',
                    active: _section == _WorkoutSection.cardio,
                    onTap: () =>
                        setState(() => _section = _WorkoutSection.cardio),
                  ),
                  const SizedBox(width: 8),
                  _SectionTab(
                    icon: Icons.fitness_center_rounded,
                    label: 'Strength',
                    active: _section == _WorkoutSection.strength,
                    onTap: () =>
                        setState(() => _section = _WorkoutSection.strength),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Active section form
              AnimatedSwitcher(
                duration: 200.ms,
                child: switch (_section) {
                  _WorkoutSection.appWorkout => _AppWorkoutForm(
                      key: const ValueKey('app'),
                      onLogged: () {
                        ref.invalidate(workoutLogsProvider);
                      },
                    ),
                  _WorkoutSection.cardio => _CardioForm(
                      key: const ValueKey('cardio'),
                      onLogged: () {
                        ref.invalidate(workoutLogsProvider);
                      },
                    ),
                  _WorkoutSection.strength => _StrengthForm(
                      key: const ValueKey('strength'),
                      onLogged: () {
                        ref.invalidate(workoutLogsProvider);
                        ref.invalidate(exerciseHistoryProvider);
                      },
                    ),
                },
              ),
            ],
          ),
        ).animate().fadeIn(duration: 400.ms),

        // ── Recent workouts ──────────────────────────────────────────────────
        const SizedBox(height: 24),
        const Text('Recent Workouts',
            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
        const SizedBox(height: 10),
        _RecentWorkouts(),
      ],
    );
  }
}

class _SectionTab extends StatelessWidget {
  const _SectionTab({
    required this.icon,
    required this.label,
    required this.active,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Expanded(
        child: GestureDetector(
          onTap: onTap,
          child: AnimatedContainer(
            duration: 150.ms,
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(
              color: active
                  ? AppColors.blue.withAlpha(40)
                  : AppColors.surfaceElevated,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                  color: active ? AppColors.blue : AppColors.border),
            ),
            child: Column(
              children: [
                Icon(icon,
                    size: 18,
                    color:
                        active ? AppColors.blue : AppColors.textMuted),
                const SizedBox(height: 3),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                    color:
                        active ? AppColors.blue : AppColors.textMuted,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

// ── Rest-day toggle ────────────────────────────────────────────────────────────

class _RestDayToggle extends StatelessWidget {
  const _RestDayToggle({required this.value, required this.onChanged});
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: () => onChanged(!value),
        child: AnimatedContainer(
          duration: 150.ms,
          padding:
              const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          decoration: BoxDecoration(
            color: value
                ? AppColors.textMuted.withAlpha(40)
                : AppColors.surfaceElevated,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
                color: value
                    ? AppColors.textMuted
                    : AppColors.border),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.hotel_rounded,
                  size: 14,
                  color: value
                      ? AppColors.textSecondary
                      : AppColors.textMuted),
              const SizedBox(width: 5),
              Text(
                'Rest day',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: value
                      ? AppColors.textSecondary
                      : AppColors.textMuted,
                ),
              ),
            ],
          ),
        ),
      );
}

Widget _successBanner(String msg) => Container(
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
            child: Text(msg,
                style: const TextStyle(
                    color: AppColors.emerald, fontSize: 13)),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 300.ms);

// ── App Workout form ───────────────────────────────────────────────────────────

class _AppWorkoutForm extends ConsumerStatefulWidget {
  const _AppWorkoutForm({super.key, required this.onLogged});
  final VoidCallback onLogged;

  @override
  ConsumerState<_AppWorkoutForm> createState() => _AppWorkoutFormState();
}

class _AppWorkoutFormState extends ConsumerState<_AppWorkoutForm> {
  final _calCtrl = TextEditingController();
  bool _isRest = false;
  bool _loading = false;
  String? _success;

  @override
  void dispose() {
    _calCtrl.dispose();
    super.dispose();
  }

  Future<void> _log() async {
    if (!_isRest && _calCtrl.text.trim().isEmpty) return;
    setState(() { _loading = true; _success = null; });
    try {
      final logs = await WorkoutApi.logSectioned(
        section: 'app_workout',
        isRestDay: _isRest,
        caloriesFromApp: _isRest ? null : double.tryParse(_calCtrl.text),
      );
      final totalKcal = logs.fold<double>(0, (s, l) => s + (l.caloriesBurned ?? 0));
      setState(() {
        _success = _isRest
            ? 'Rest day logged!'
            : '${totalKcal.toInt()} kcal logged!';
        _calCtrl.clear();
        _isRest = false;
      });
      widget.onLogged();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Calories from app / watch',
                  style: TextStyle(
                      color: AppColors.textSecondary, fontSize: 13)),
              _RestDayToggle(
                  value: _isRest,
                  onChanged: (v) => setState(() => _isRest = v)),
            ],
          ),
          const SizedBox(height: 12),

          if (!_isRest)
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
                    child: TextField(
                      controller: _calCtrl,
                      keyboardType: TextInputType.number,
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
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
                  ),
                ],
              ),
            ),

          if (_success != null) ...[
            const SizedBox(height: 12),
            _successBanner(_success!),
          ],
          const SizedBox(height: 12),

          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _loading ? null : _log,
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.blue),
              icon: _loading
                  ? const SizedBox(
                      width: 16, height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.local_fire_department_rounded, size: 16),
              label: Text(_loading
                  ? 'Logging...'
                  : _isRest
                      ? 'Log Rest Day'
                      : 'Log Workout'),
            ),
          ),
        ],
      );
}

// ── Cardio form ────────────────────────────────────────────────────────────────

class _CardioEntry {
  final activityCtrl = TextEditingController();
  final durationCtrl = TextEditingController();
  final caloriesCtrl = TextEditingController();
  void dispose() {
    activityCtrl.dispose();
    durationCtrl.dispose();
    caloriesCtrl.dispose();
  }
  bool get isValid =>
      activityCtrl.text.trim().isNotEmpty && durationCtrl.text.trim().isNotEmpty;
}

class _CardioForm extends ConsumerStatefulWidget {
  const _CardioForm({super.key, required this.onLogged});
  final VoidCallback onLogged;

  @override
  ConsumerState<_CardioForm> createState() => _CardioFormState();
}

class _CardioFormState extends ConsumerState<_CardioForm> {
  final List<_CardioEntry> _rows = [_CardioEntry()];
  bool _isRest = false;
  bool _loading = false;
  String? _success;

  @override
  void dispose() {
    for (final r in _rows) { r.dispose(); }
    super.dispose();
  }

  Future<void> _log() async {
    setState(() { _loading = true; _success = null; });
    try {
      if (_isRest) {
        await WorkoutApi.logSectioned(section: 'rest_day', isRestDay: true);
        setState(() => _success = 'Rest day logged!');
        widget.onLogged();
        return;
      }
      final valid = _rows.where((r) => r.isValid).toList();
      if (valid.isEmpty) return;
      final activities = valid.map((r) => {
        'activity_description': r.activityCtrl.text.trim(),
        'duration_minutes': double.tryParse(r.durationCtrl.text) ?? 0,
        if (r.caloriesCtrl.text.trim().isNotEmpty)
          'calories_burned': double.tryParse(r.caloriesCtrl.text),
      }).toList();
      final logs = await WorkoutApi.logSectioned(
          section: 'cardio', cardioActivities: activities);
      final totalKcal = logs.fold<double>(0, (s, l) => s + (l.caloriesBurned ?? 0));
      setState(() {
        _success = '${logs.length} activit${logs.length != 1 ? "ies" : "y"} logged · ${totalKcal.toInt()} kcal';
        for (final r in _rows) { r.dispose(); }
        _rows
          ..clear()
          ..add(_CardioEntry());
      });
      widget.onLogged();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Expanded(
                child: Text(
                  'Omit calories to let AI estimate from your weight.',
                  style: TextStyle(
                      color: AppColors.textSecondary, fontSize: 12),
                ),
              ),
              const SizedBox(width: 8),
              _RestDayToggle(
                  value: _isRest,
                  onChanged: (v) => setState(() => _isRest = v)),
            ],
          ),
          const SizedBox(height: 12),

          if (!_isRest) ...[
            // Column headers
            const Padding(
              padding: EdgeInsets.only(left: 2, bottom: 6),
              child: Row(
                children: [
                  Expanded(
                      flex: 5,
                      child: Text('Activity',
                          style: TextStyle(
                              color: AppColors.textMuted, fontSize: 11))),
                  SizedBox(width: 6),
                  SizedBox(
                      width: 44,
                      child: Text('Min',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                              color: AppColors.textMuted, fontSize: 11))),
                  SizedBox(width: 6),
                  SizedBox(
                      width: 50,
                      child: Text('kcal opt',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                              color: AppColors.textMuted, fontSize: 11))),
                  SizedBox(width: 28),
                ],
              ),
            ),
            ..._rows.asMap().entries.map((e) => _CardioRow(
                  entry: e.value,
                  canRemove: _rows.length > 1,
                  onRemove: () => setState(() {
                    _rows[e.key].dispose();
                    _rows.removeAt(e.key);
                  }),
                  onChanged: () => setState(() {}),
                )),
            TextButton.icon(
              onPressed: () => setState(() => _rows.add(_CardioEntry())),
              icon: const Icon(Icons.add_rounded,
                  size: 18, color: AppColors.blue),
              label: const Text('Add activity',
                  style: TextStyle(color: AppColors.blue, fontSize: 13)),
              style: TextButton.styleFrom(padding: EdgeInsets.zero),
            ),
          ],

          if (_success != null) ...[
            const SizedBox(height: 8),
            _successBanner(_success!),
          ],
          const SizedBox(height: 12),

          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: (_loading ||
                      (!_isRest && _rows.every((r) => !r.isValid)))
                  ? null
                  : _log,
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.blue),
              icon: _loading
                  ? const SizedBox(
                      width: 16, height: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.directions_bike_rounded, size: 16),
              label: Text(_loading
                  ? 'Estimating...'
                  : _isRest
                      ? 'Log Rest Day'
                      : 'Log Cardio'),
            ),
          ),
        ],
      );
}

class _CardioRow extends StatelessWidget {
  const _CardioRow({
    required this.entry,
    required this.canRemove,
    required this.onRemove,
    required this.onChanged,
  });
  final _CardioEntry entry;
  final bool canRemove;
  final VoidCallback onRemove;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 5,
              child: TextField(
                controller: entry.activityCtrl,
                onChanged: (_) => onChanged(),
                decoration:
                    const InputDecoration(hintText: 'Treadmill, Cycling…'),
              ),
            ),
            const SizedBox(width: 6),
            SizedBox(
              width: 44,
              child: TextField(
                controller: entry.durationCtrl,
                onChanged: (_) => onChanged(),
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                textAlign: TextAlign.center,
                decoration: const InputDecoration(hintText: '10'),
              ),
            ),
            const SizedBox(width: 6),
            SizedBox(
              width: 50,
              child: TextField(
                controller: entry.caloriesCtrl,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                textAlign: TextAlign.center,
                decoration: const InputDecoration(hintText: '—'),
              ),
            ),
            SizedBox(
              width: 28,
              child: canRemove
                  ? IconButton(
                      padding: EdgeInsets.zero,
                      icon: const Icon(Icons.close_rounded,
                          size: 18, color: AppColors.textMuted),
                      onPressed: onRemove,
                    )
                  : const SizedBox.shrink(),
            ),
          ],
        ),
      );
}

// ── Strength form ──────────────────────────────────────────────────────────────

class _StrEntry {
  final nameCtrl = TextEditingController();
  final setsCtrl = TextEditingController();
  final repsCtrl = TextEditingController();
  final weightCtrl = TextEditingController();

  void dispose() {
    nameCtrl.dispose();
    setsCtrl.dispose();
    repsCtrl.dispose();
    weightCtrl.dispose();
  }

  bool get isValid => nameCtrl.text.trim().isNotEmpty;
}

class _StrengthForm extends ConsumerStatefulWidget {
  const _StrengthForm({super.key, required this.onLogged});
  final VoidCallback onLogged;

  @override
  ConsumerState<_StrengthForm> createState() => _StrengthFormState();
}

class _StrengthFormState extends ConsumerState<_StrengthForm> {
  final List<_StrEntry> _rows = [_StrEntry()];
  bool _isRest = false;
  bool _loading = false;
  String? _success;

  @override
  void dispose() {
    for (final r in _rows) { r.dispose(); }
    super.dispose();
  }

  Future<void> _log() async {
    setState(() { _loading = true; _success = null; });
    try {
      if (_isRest) {
        await WorkoutApi.logSectioned(section: 'rest_day', isRestDay: true);
        setState(() => _success = 'Rest day logged!');
        widget.onLogged();
        return;
      }
      final valid = _rows.where((r) => r.isValid).toList();
      if (valid.isEmpty) return;
      final exercises = valid.map((r) => {
        'name': r.nameCtrl.text.trim(),
        'sets': int.tryParse(r.setsCtrl.text) ?? 1,
        'reps': int.tryParse(r.repsCtrl.text) ?? 1,
        'weight_kg': double.tryParse(r.weightCtrl.text) ?? 0.0,
      }).toList();
      final logs = await WorkoutApi.logSectioned(
          section: 'strength', strengthExercises: exercises);
      final totalKcal = logs.fold<double>(0, (s, l) => s + (l.caloriesBurned ?? 0));
      setState(() {
        _success =
            '${logs.length} exercise${logs.length != 1 ? 's' : ''} logged · ${totalKcal.toInt()} kcal';
        for (final r in _rows) { r.dispose(); }
        _rows
          ..clear()
          ..add(_StrEntry());
      });
      widget.onLogged();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final historyAsync = ref.watch(exerciseHistoryProvider);
    final history = historyAsync.value ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('AI estimates calories from sets × reps × weight.',
                style: TextStyle(
                    color: AppColors.textSecondary, fontSize: 12)),
            _RestDayToggle(
                value: _isRest,
                onChanged: (v) => setState(() => _isRest = v)),
          ],
        ),
        const SizedBox(height: 12),

        if (!_isRest) ...[
          const Padding(
            padding: EdgeInsets.only(left: 2, bottom: 6),
            child: Row(
              children: [
                Expanded(
                    flex: 5,
                    child: Text('Exercise',
                        style: TextStyle(
                            color: AppColors.textMuted, fontSize: 11))),
                SizedBox(width: 6),
                SizedBox(
                    width: 36,
                    child: Text('Sets',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            color: AppColors.textMuted, fontSize: 11))),
                SizedBox(width: 6),
                SizedBox(
                    width: 36,
                    child: Text('Reps',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            color: AppColors.textMuted, fontSize: 11))),
                SizedBox(width: 6),
                SizedBox(
                    width: 44,
                    child: Text('kg',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            color: AppColors.textMuted, fontSize: 11))),
                SizedBox(width: 28),
              ],
            ),
          ),
          ..._rows.asMap().entries.map((e) => _StrRow(
                entry: e.value,
                history: history,
                canRemove: _rows.length > 1,
                onRemove: () => setState(() {
                  _rows[e.key].dispose();
                  _rows.removeAt(e.key);
                }),
                onChanged: () => setState(() {}),
              )),
          TextButton.icon(
            onPressed: () => setState(() => _rows.add(_StrEntry())),
            icon: const Icon(Icons.add_rounded,
                size: 18, color: AppColors.blue),
            label: const Text('Add exercise',
                style: TextStyle(color: AppColors.blue, fontSize: 13)),
            style: TextButton.styleFrom(padding: EdgeInsets.zero),
          ),
        ],

        if (_success != null) ...[
          const SizedBox(height: 8),
          _successBanner(_success!),
        ],
        const SizedBox(height: 12),

        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: (_loading ||
                    (!_isRest && _rows.every((r) => !r.isValid)))
                ? null
                : _log,
            style:
                ElevatedButton.styleFrom(backgroundColor: AppColors.blue),
            icon: _loading
                ? const SizedBox(
                    width: 16, height: 16,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white),
                  )
                : const Icon(Icons.fitness_center_rounded, size: 16),
            label: Text(_loading
                ? 'Estimating...'
                : _isRest
                    ? 'Log Rest Day'
                    : 'Log Strength'),
          ),
        ),
      ],
    );
  }
}

class _StrRow extends StatelessWidget {
  const _StrRow({
    required this.entry,
    required this.history,
    required this.canRemove,
    required this.onRemove,
    required this.onChanged,
  });
  final _StrEntry entry;
  final List<String> history;
  final bool canRemove;
  final VoidCallback onRemove;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 5,
              child: RawAutocomplete<String>(
                textEditingController: entry.nameCtrl,
                focusNode: FocusNode(),
                optionsBuilder: (v) {
                  if (v.text.isEmpty) return const [];
                  return history.where((n) =>
                      n.toLowerCase().contains(v.text.toLowerCase()));
                },
                displayStringForOption: (o) => o,
                fieldViewBuilder: (_, ctrl, focus, submit) => TextField(
                  controller: ctrl,
                  focusNode: focus,
                  onChanged: (_) => onChanged(),
                  textCapitalization: TextCapitalization.words,
                  decoration: const InputDecoration(hintText: 'Bench Press…'),
                  onEditingComplete: submit,
                ),
                optionsViewBuilder: (_, onSel, opts) => Align(
                  alignment: Alignment.topLeft,
                  child: Material(
                    color: AppColors.surfaceElevated,
                    borderRadius: BorderRadius.circular(10),
                    elevation: 4,
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(
                          maxHeight: 180, maxWidth: 200),
                      child: ListView(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        shrinkWrap: true,
                        children: opts.map((o) => InkWell(
                              onTap: () => onSel(o),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 12, vertical: 10),
                                child: Text(o,
                                    style: const TextStyle(
                                        fontSize: 13,
                                        color: AppColors.textPrimary)),
                              ),
                            )).toList(),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 6),
            SizedBox(
              width: 36,
              child: TextField(
                controller: entry.setsCtrl,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                textAlign: TextAlign.center,
                decoration: const InputDecoration(hintText: '3'),
              ),
            ),
            const SizedBox(width: 6),
            SizedBox(
              width: 36,
              child: TextField(
                controller: entry.repsCtrl,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                textAlign: TextAlign.center,
                decoration: const InputDecoration(hintText: '10'),
              ),
            ),
            const SizedBox(width: 6),
            SizedBox(
              width: 44,
              child: TextField(
                controller: entry.weightCtrl,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                textAlign: TextAlign.center,
                decoration: const InputDecoration(hintText: '0'),
              ),
            ),
            SizedBox(
              width: 28,
              child: canRemove
                  ? IconButton(
                      padding: EdgeInsets.zero,
                      icon: const Icon(Icons.close_rounded,
                          size: 18, color: AppColors.textMuted),
                      onPressed: onRemove,
                    )
                  : const SizedBox.shrink(),
            ),
          ],
        ),
      );
}

// ── Recent workouts list ───────────────────────────────────────────────────────

class _RecentWorkouts extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final logsAsync = ref.watch(workoutLogsProvider);

    return logsAsync.when(
      loading: () =>
          const Center(child: CircularProgressIndicator()),
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
                final icon = log.isRestDay
                    ? Icons.hotel_rounded
                    : log.workoutSection == 'cardio'
                        ? Icons.directions_bike_rounded
                        : log.workoutSection == 'strength'
                            ? Icons.fitness_center_rounded
                            : Icons.smartphone_rounded;
                final subtitle = log.isRestDay
                    ? 'Rest day'
                    : '${log.workoutSection == 'cardio' ? 'Cardio' : log.workoutSection == 'strength' ? 'Strength' : 'App'}'
                      '${log.durationMinutes > 0 ? ' · ${log.durationMinutes} min' : ''}'
                      '${log.exercises.isNotEmpty ? ' · ${log.exercises.length} exercises' : ''}';

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
                        child: Icon(icon,
                            color: AppColors.blue, size: 20),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(log.title,
                                style: const TextStyle(
                                    fontWeight: FontWeight.w500,
                                    fontSize: 14)),
                            Text(subtitle,
                                style: const TextStyle(
                                    color: AppColors.textMuted,
                                    fontSize: 12)),
                          ],
                        ),
                      ),
                      if (log.caloriesBurned != null &&
                          log.caloriesBurned! > 0)
                        Text(
                          '${log.caloriesBurned!.toInt()} kcal',
                          style: const TextStyle(
                              fontWeight: FontWeight.w600,
                              fontSize: 14,
                              color: AppColors.amber),
                        ),
                    ],
                  ),
                ).animate().fadeIn(
                    delay: (i * 40).ms, duration: 300.ms);
              }).toList(),
            ),
    );
  }
}
