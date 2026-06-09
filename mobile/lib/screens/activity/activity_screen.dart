import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/models/step_log.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/activity_provider.dart';
import '../../providers/auth_provider.dart';
import '../../providers/health_connect_provider.dart';
import '../../widgets/progress_ring.dart';

class ActivityScreen extends ConsumerStatefulWidget {
  const ActivityScreen({super.key});

  @override
  ConsumerState<ActivityScreen> createState() => _ActivityScreenState();
}

class _ActivityScreenState extends ConsumerState<ActivityScreen> {
  final _stepsCtrl = TextEditingController();
  bool _saving = false;

  @override
  void dispose() {
    _stepsCtrl.dispose();
    super.dispose();
  }

  // Pre-fill input with today's logged steps
  void _prefillToday(List<StepLog> logs) {
    final today = DateTime.now();
    final todayLog = logs.firstWhere(
      (l) =>
          l.date.year == today.year &&
          l.date.month == today.month &&
          l.date.day == today.day,
      orElse: () => StepLog(id: '', date: today, steps: 0),
    );
    if (todayLog.steps > 0 && _stepsCtrl.text.isEmpty) {
      _stepsCtrl.text = todayLog.steps.toString();
    }
  }

  Future<void> _save() async {
    final steps = int.tryParse(_stepsCtrl.text);
    if (steps == null || steps <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter a valid step count')),
      );
      return;
    }
    setState(() => _saving = true);
    try {
      await ref.read(stepHistoryProvider.notifier).logSteps(steps);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('$steps steps saved!'),
            backgroundColor: AppColors.emerald,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _showTargetDialog(int current) async {
    final ctrl = TextEditingController(text: current.toString());
    final result = await showDialog<int>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: const Text('Daily Steps Target'),
        content: TextField(
          controller: ctrl,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: const InputDecoration(
            hintText: '10000',
            suffixText: 'steps',
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              final v = int.tryParse(ctrl.text);
              if (v != null && v > 0) Navigator.pop(ctx, v);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (result != null && mounted) {
      await ref.read(authProvider.notifier).updateProfile({'daily_steps_target': result});
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider).user;
    final historyAsync = ref.watch(stepHistoryProvider);
    final weightKg = user?.weightKg ?? 70.0;
    final heightCm = user?.heightCm ?? 170.0;
    final age = user?.age ?? 25;
    final gender = user?.gender ?? 'other';
    final stepsTarget = user?.dailyStepsTarget ?? 10000;

    // BMR
    final bmr = calculateBmr(
      weightKg: weightKg,
      heightCm: heightCm,
      age: age,
      gender: gender,
    );

    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppColors.background,
        surfaceTintColor: Colors.transparent,
        title: const Text('Activity', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          TextButton.icon(
            onPressed: () => _showTargetDialog(stepsTarget),
            icon: const Icon(Icons.flag_rounded, size: 16, color: AppColors.emerald),
            label: Text(
              'Target: ${_fmt(stepsTarget)}',
              style: const TextStyle(color: AppColors.emerald, fontSize: 13),
            ),
          ),
        ],
      ),
      body: historyAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Text(e.toString(), style: const TextStyle(color: AppColors.red)),
        ),
        data: (logs) {
          _prefillToday(logs);

          final today = DateTime.now();
          final todayLog = logs.firstWhere(
            (l) =>
                l.date.year == today.year &&
                l.date.month == today.month &&
                l.date.day == today.day,
            orElse: () => StepLog(id: '', date: today, steps: 0),
          );
          final todaySteps = todayLog.steps;
          final progress = (todaySteps / stepsTarget).clamp(0.0, 1.0);
          final distanceKm = stepsToKm(steps: todaySteps, heightCm: heightCm);
          final activeCal = stepsToCalories(
              steps: todaySteps, weightKg: weightKg, heightCm: heightCm);

          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
            children: [
              // ── Today's ring card ────────────────────────────────────────
              _TodayCard(
                progress: progress,
                steps: todaySteps,
                target: stepsTarget,
                distanceKm: distanceKm,
                activeCal: activeCal,
                bmr: bmr,
              ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.05, end: 0),
              const SizedBox(height: 16),

              // ── Health Connect sync ──────────────────────────────────────
              _HealthConnectCard().animate().fadeIn(delay: 100.ms, duration: 400.ms),
              const SizedBox(height: 16),

              // ── Log steps input ──────────────────────────────────────────
              _LogStepsCard(
                controller: _stepsCtrl,
                saving: _saving,
                onSave: _save,
              ).animate().fadeIn(delay: 150.ms, duration: 400.ms),
              const SizedBox(height: 20),

              // ── 7-day bar chart ──────────────────────────────────────────
              if (logs.isNotEmpty) ...[
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Last 7 Days',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    Text(
                      'Target: ${_fmt(stepsTarget)} steps',
                      style: const TextStyle(
                          color: AppColors.textMuted, fontSize: 12),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                _StepsBarChart(logs: logs, target: stepsTarget)
                    .animate()
                    .fadeIn(delay: 200.ms, duration: 400.ms),
                const SizedBox(height: 20),

                // ── Stats row ──────────────────────────────────────────────
                _WeeklyStats(logs: logs, weightKg: weightKg, heightCm: heightCm)
                    .animate()
                    .fadeIn(delay: 300.ms, duration: 400.ms),
              ],

              // ── BMR info card ────────────────────────────────────────────
              const SizedBox(height: 20),
              _BmrInfoCard(bmr: bmr, gender: gender)
                  .animate()
                  .fadeIn(delay: 350.ms, duration: 400.ms),
            ],
          );
        },
      ),
    );
  }

  String _fmt(int n) => NumberFormat('#,###').format(n);
}

// ── Today card with ring ──────────────────────────────────────────────────────

class _TodayCard extends StatelessWidget {
  const _TodayCard({
    required this.progress,
    required this.steps,
    required this.target,
    required this.distanceKm,
    required this.activeCal,
    required this.bmr,
  });
  final double progress;
  final int steps, target;
  final double distanceKm, activeCal, bmr;

  @override
  Widget build(BuildContext context) {
    final totalBurned = bmr + activeCal;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ProgressRing(
                progress: progress,
                size: 130,
                strokeWidth: 10,
                color: AppColors.emerald,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      NumberFormat('#,###').format(steps),
                      style: const TextStyle(
                          fontSize: 24, fontWeight: FontWeight.bold),
                    ),
                    const Text('steps',
                        style: TextStyle(
                            fontSize: 11, color: AppColors.textMuted)),
                    const SizedBox(height: 2),
                    Text(
                      '${(progress * 100).toInt()}%',
                      style: const TextStyle(
                          fontSize: 11,
                          color: AppColors.emerald,
                          fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                  child: _StatChip(
                icon: Icons.straighten_rounded,
                label: 'Distance',
                value: '${distanceKm.toStringAsFixed(2)} km',
                color: AppColors.blue,
              )),
              const SizedBox(width: 8),
              Expanded(
                  child: _StatChip(
                icon: Icons.directions_walk_rounded,
                label: 'Active cal',
                value: '${activeCal.toInt()} kcal',
                color: AppColors.amber,
              )),
              const SizedBox(width: 8),
              Expanded(
                  child: _StatChip(
                icon: Icons.favorite_rounded,
                label: 'Total burn',
                value: '${totalBurned.toInt()} kcal',
                color: AppColors.purple,
              )),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  const _StatChip(
      {required this.icon,
      required this.label,
      required this.value,
      required this.color});
  final IconData icon;
  final String label, value;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: color.withAlpha(20),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withAlpha(40)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 18),
            const SizedBox(height: 4),
            Text(value,
                style: TextStyle(
                    fontSize: 12, fontWeight: FontWeight.bold, color: color)),
            Text(label,
                style: const TextStyle(
                    fontSize: 10, color: AppColors.textMuted)),
          ],
        ),
      );
}

// ── Log steps input ───────────────────────────────────────────────────────────

class _LogStepsCard extends StatelessWidget {
  const _LogStepsCard(
      {required this.controller,
      required this.saving,
      required this.onSave});
  final TextEditingController controller;
  final bool saving;
  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            const Icon(Icons.directions_walk_rounded,
                color: AppColors.emerald, size: 24),
            const SizedBox(width: 12),
            Expanded(
              child: TextField(
                controller: controller,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: const InputDecoration(
                  hintText: "Today's steps",
                  suffixText: 'steps',
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  contentPadding: EdgeInsets.zero,
                  isDense: true,
                ),
                style: const TextStyle(
                    fontSize: 20, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(width: 12),
            ElevatedButton(
              onPressed: saving ? null : onSave,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.emerald,
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
              child: saving
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Text('Save'),
            ),
          ],
        ),
      );
}

// ── 7-day bar chart ───────────────────────────────────────────────────────────

class _StepsBarChart extends StatelessWidget {
  const _StepsBarChart({required this.logs, required this.target});
  final List<StepLog> logs;
  final int target;

  @override
  Widget build(BuildContext context) {
    // Build a map date→steps for the last 7 days
    final today = DateTime.now();
    final days = List.generate(7, (i) {
      final d = today.subtract(Duration(days: 6 - i));
      return DateTime(d.year, d.month, d.day);
    });

    final stepsMap = {
      for (final l in logs)
        DateTime(l.date.year, l.date.month, l.date.day): l.steps,
    };

    final maxSteps =
        (logs.isEmpty ? target.toDouble() : logs.map((l) => l.steps).reduce((a, b) => a > b ? a : b).toDouble())
            .clamp(target.toDouble(), double.infinity);

    return Container(
      height: 180,
      padding: const EdgeInsets.fromLTRB(8, 16, 8, 0),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: BarChart(
        BarChartData(
          maxY: maxSteps * 1.15,
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            getDrawingHorizontalLine: (_) => const FlLine(
                color: AppColors.border, strokeWidth: 1),
            horizontalInterval: maxSteps / 4,
          ),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, _) {
                  final idx = value.toInt();
                  if (idx < 0 || idx >= 7) return const SizedBox.shrink();
                  final d = days[idx];
                  final isToday = idx == 6;
                  return Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      isToday ? 'Today' : DateFormat('E').format(d),
                      style: TextStyle(
                        fontSize: 10,
                        color: isToday ? AppColors.emerald : AppColors.textMuted,
                        fontWeight: isToday ? FontWeight.bold : FontWeight.normal,
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
          // Target line
          extraLinesData: ExtraLinesData(
            horizontalLines: [
              HorizontalLine(
                y: target.toDouble(),
                color: AppColors.emerald.withAlpha(120),
                strokeWidth: 1.5,
                dashArray: [6, 4],
                label: HorizontalLineLabel(
                  show: true,
                  alignment: Alignment.topRight,
                  padding: const EdgeInsets.only(right: 4, bottom: 2),
                  style: const TextStyle(
                      color: AppColors.emerald, fontSize: 9),
                  labelResolver: (_) => 'target',
                ),
              ),
            ],
          ),
          barGroups: List.generate(7, (i) {
            final d = days[i];
            final steps = stepsMap[d] ?? 0;
            final hitTarget = steps >= target;
            final isToday = i == 6;
            return BarChartGroupData(
              x: i,
              barRods: [
                BarChartRodData(
                  toY: steps.toDouble(),
                  color: hitTarget
                      ? AppColors.emerald
                      : isToday
                          ? AppColors.blue
                          : AppColors.emerald.withAlpha(80),
                  width: 22,
                  borderRadius: const BorderRadius.vertical(
                      top: Radius.circular(6)),
                ),
              ],
            );
          }),
        ),
      ),
    );
  }
}

// ── Weekly stats ──────────────────────────────────────────────────────────────

class _WeeklyStats extends StatelessWidget {
  const _WeeklyStats(
      {required this.logs,
      required this.weightKg,
      required this.heightCm});
  final List<StepLog> logs;
  final double weightKg, heightCm;

  @override
  Widget build(BuildContext context) {
    if (logs.isEmpty) return const SizedBox.shrink();
    final totalSteps = logs.fold(0, (s, l) => s + l.steps);
    final avgSteps = totalSteps ~/ logs.length;
    final totalKm =
        stepsToKm(steps: totalSteps, heightCm: heightCm);
    final totalCal =
        stepsToCalories(steps: totalSteps, weightKg: weightKg, heightCm: heightCm);
    final daysHit = logs.where((l) => l.steps >= 10000).length;

    return Row(
      children: [
        Expanded(
            child: _WeekStat(
                label: 'Avg steps', value: NumberFormat('#,###').format(avgSteps))),
        const SizedBox(width: 8),
        Expanded(
            child: _WeekStat(
                label: 'Total km',
                value: totalKm.toStringAsFixed(1),
                unit: 'km')),
        const SizedBox(width: 8),
        Expanded(
            child: _WeekStat(
                label: 'Cal burned',
                value: totalCal.toInt().toString(),
                unit: 'kcal')),
        const SizedBox(width: 8),
        Expanded(
            child: _WeekStat(
                label: 'Goal days',
                value: '$daysHit/${logs.length}',
                color: daysHit >= logs.length ~/ 2
                    ? AppColors.emerald
                    : AppColors.amber)),
      ],
    );
  }
}

class _WeekStat extends StatelessWidget {
  const _WeekStat(
      {required this.label,
      required this.value,
      this.unit,
      this.color});
  final String label, value;
  final String? unit;
  final Color? color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          children: [
            RichText(
              text: TextSpan(
                children: [
                  TextSpan(
                    text: value,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: color ?? AppColors.textPrimary,
                    ),
                  ),
                  if (unit != null)
                    TextSpan(
                      text: ' $unit',
                      style: const TextStyle(
                          fontSize: 10, color: AppColors.textMuted),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 2),
            Text(label,
                style: const TextStyle(
                    fontSize: 10, color: AppColors.textMuted),
                textAlign: TextAlign.center),
          ],
        ),
      );
}

// ── BMR info card ─────────────────────────────────────────────────────────────

class _BmrInfoCard extends StatelessWidget {
  const _BmrInfoCard({required this.bmr, required this.gender});
  final double bmr;
  final String gender;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.purple.withAlpha(15),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.purple.withAlpha(40)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppColors.purple.withAlpha(30),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.favorite_rounded,
                  color: AppColors.purple, size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${bmr.toInt()} kcal/day resting burn',
                    style: const TextStyle(
                        fontWeight: FontWeight.bold, fontSize: 14),
                  ),
                  const SizedBox(height: 2),
                  const Text(
                    'Your body burns this just existing — breathing, heart, organs. '
                    'Steps add on top of this.',
                    style: TextStyle(
                        color: AppColors.textSecondary, fontSize: 12, height: 1.4),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

// ── Health Connect sync card ──────────────────────────────────────────────────

class _HealthConnectCard extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hc = ref.watch(healthConnectProvider);

    if (hc.status == HcStatus.unavailable) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.surfaceElevated,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.border),
        ),
        child: const Row(
          children: [
            Icon(Icons.health_and_safety_outlined,
                color: AppColors.textMuted, size: 20),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'Google Health Connect is not available on this device.',
                style: TextStyle(color: AppColors.textMuted, fontSize: 13),
              ),
            ),
          ],
        ),
      );
    }

    final isSyncing = hc.status == HcStatus.syncing || hc.status == HcStatus.checking;
    final needsPermission = hc.status == HcStatus.permissionDenied;
    final summary = hc.lastSummary;
    final syncedAt = hc.lastSyncedAt;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: hc.hasSyncedToday
              ? AppColors.emerald.withAlpha(80)
              : AppColors.border,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.emerald.withAlpha(25),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.health_and_safety_rounded,
                    color: AppColors.emerald, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Google Health Connect',
                      style: TextStyle(
                          fontWeight: FontWeight.w600, fontSize: 14),
                    ),
                    Text(
                      needsPermission
                          ? 'Permission required'
                          : hc.hasSyncedToday
                              ? 'Synced today · ${_fmt(syncedAt!)}'
                              : syncedAt != null
                                  ? 'Last synced ${_fmtDate(syncedAt)}'
                                  : 'Not synced yet',
                      style: TextStyle(
                        color: needsPermission
                            ? AppColors.amber
                            : hc.hasSyncedToday
                                ? AppColors.emerald
                                : AppColors.textMuted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              // Action button
              isSyncing
                  ? const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                          strokeWidth: 2.5, color: AppColors.emerald),
                    )
                  : needsPermission
                      ? _ActionButton(
                          label: 'Connect',
                          color: AppColors.amber,
                          onTap: () =>
                              ref.read(healthConnectProvider.notifier)
                                  .requestPermissions(),
                        )
                      : _ActionButton(
                          label: 'Sync',
                          color: AppColors.emerald,
                          onTap: () =>
                              ref.read(healthConnectProvider.notifier)
                                  .syncToday(),
                        ),
            ],
          ),

          // Error message
          if (hc.status == HcStatus.error && hc.errorMessage != null) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.red.withAlpha(20),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                hc.errorMessage!,
                style:
                    const TextStyle(color: AppColors.red, fontSize: 12),
              ),
            ),
          ],

          // Synced data chips
          if (summary != null && hc.hasSyncedToday) ...[
            const SizedBox(height: 14),
            Row(
              children: [
                _HcChip(
                  icon: Icons.directions_walk_rounded,
                  label: 'Steps',
                  value: NumberFormat('#,###').format(summary.steps),
                  color: AppColors.blue,
                ),
                const SizedBox(width: 8),
                _HcChip(
                  icon: Icons.local_fire_department_rounded,
                  label: 'Active cal',
                  value:
                      '${summary.activeCaloriesBurned.toInt()} kcal',
                  color: AppColors.amber,
                ),
                if (summary.workouts.isNotEmpty) ...[
                  const SizedBox(width: 8),
                  _HcChip(
                    icon: Icons.fitness_center_rounded,
                    label: 'Workouts',
                    value: summary.workouts.length.toString(),
                    color: AppColors.purple,
                  ),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }

  String _fmt(DateTime dt) => DateFormat('h:mm a').format(dt);
  String _fmtDate(DateTime dt) => DateFormat('MMM d').format(dt);
}

class _ActionButton extends StatelessWidget {
  const _ActionButton(
      {required this.label, required this.color, required this.onTap});
  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding:
              const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
          decoration: BoxDecoration(
            color: color.withAlpha(25),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: color.withAlpha(60)),
          ),
          child: Text(label,
              style: TextStyle(
                  color: color,
                  fontSize: 13,
                  fontWeight: FontWeight.w600)),
        ),
      );
}

class _HcChip extends StatelessWidget {
  const _HcChip(
      {required this.icon,
      required this.label,
      required this.value,
      required this.color});
  final IconData icon;
  final String label, value;
  final Color color;

  @override
  Widget build(BuildContext context) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 6),
          decoration: BoxDecoration(
            color: color.withAlpha(18),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: color.withAlpha(35)),
          ),
          child: Column(
            children: [
              Icon(icon, color: color, size: 16),
              const SizedBox(height: 3),
              Text(value,
                  style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: color)),
              Text(label,
                  style: const TextStyle(
                      fontSize: 9, color: AppColors.textMuted)),
            ],
          ),
        ),
      );
}
