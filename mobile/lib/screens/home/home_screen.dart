import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api/analytics_api.dart';
import '../../core/models/analytics.dart';
import '../../core/models/step_log.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/activity_provider.dart';
import '../../providers/auth_provider.dart';
import '../../providers/food_provider.dart';
import '../../providers/workout_provider.dart';
import '../../widgets/progress_ring.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).user;
    final foodAsync = ref.watch(todayFoodProvider);
    final stepHistoryAsync = ref.watch(stepHistoryProvider);
    final today = DateFormat('EEEE, MMM d').format(DateTime.now());

    // Compute today's burned calories from steps + BMR
    final weightKg = user?.weightKg ?? 70.0;
    final heightCm = user?.heightCm ?? 170.0;
    final age = user?.age ?? 25;
    final gender = user?.gender ?? 'other';
    final bmr = calculateBmr(weightKg: weightKg, heightCm: heightCm, age: age, gender: gender);
    final todayLog = stepHistoryAsync.value?.firstWhere(
      (l) {
        final now = DateTime.now();
        return l.date.year == now.year && l.date.month == now.month && l.date.day == now.day;
      },
      orElse: () => StepLog(id: '', date: DateTime.now(), steps: 0),
    );
    final stepCal = todayLog != null ? stepsToCalories(steps: todayLog.steps, weightKg: weightKg, heightCm: heightCm) : 0.0;
    final totalBurned = bmr + stepCal;

    return Scaffold(
      body: RefreshIndicator(
        color: AppColors.emerald,
        backgroundColor: AppColors.surface,
        onRefresh: () => ref.read(todayFoodProvider.notifier).load(),
        child: CustomScrollView(
          slivers: [
            // App bar
            SliverAppBar(
              floating: true,
              backgroundColor: AppColors.background,
              surfaceTintColor: Colors.transparent,
              title: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Good ${_greeting()}, ${user?.displayName.split(' ').first ?? 'there'} 👋',
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                  ),
                  Text(today, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
                ],
              ),
              actions: [
                Padding(
                  padding: const EdgeInsets.only(right: 16),
                  child: CircleAvatar(
                    radius: 18,
                    backgroundColor: AppColors.emerald.withAlpha(51),
                    child: Text(
                      user?.displayName.isNotEmpty == true
                          ? user!.displayName[0].toUpperCase()
                          : '?',
                      style: const TextStyle(color: AppColors.emerald, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
              ],
            ),

            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  // ── Calorie ring card ──────────────────────────────────────
                  foodAsync.when(
                    loading: () => _CalorieCardSkeleton(),
                    error: (e, _) => _ErrorCard(message: e.toString()),
                    data: (summary) => _CalorieCard(
                      summary: summary,
                      targetCalories: user?.targetCalories?.toDouble() ?? 2000,
                      totalBurned: totalBurned,
                    ),
                  ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.1, end: 0),
                  const SizedBox(height: 16),

                  // ── Macro row ──────────────────────────────────────────────
                  foodAsync.when(
                    loading: () => const SizedBox(height: 80),
                    error: (_, __) => const SizedBox.shrink(),
                    data: (summary) => _MacroRow(
                      proteinG: summary.totalProteinG,
                      carbsG: summary.totalCarbsG,
                      fatG: summary.totalFatG,
                      proteinTarget: user?.targetProteinG ?? 150,
                      carbsTarget: user?.targetCarbsG ?? 200,
                      fatTarget: user?.targetFatG ?? 65,
                    ),
                  ).animate().fadeIn(delay: 100.ms, duration: 400.ms),
                  const SizedBox(height: 20),

                  // ── Quick actions ──────────────────────────────────────────
                  _SectionHeader(title: 'Quick Actions'),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: _QuickAction(
                          icon: Icons.restaurant_menu_rounded,
                          label: 'Log Food',
                          color: AppColors.emerald,
                          onTap: () {
                            ref.read(logTabProvider.notifier).state = 0;
                            context.go('/log');
                          },
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _QuickAction(
                          icon: Icons.fitness_center_rounded,
                          label: 'Log Workout',
                          color: AppColors.blue,
                          onTap: () {
                            ref.read(logTabProvider.notifier).state = 1;
                            context.go('/log');
                          },
                        ),
                      ),
                    ],
                  ).animate().fadeIn(delay: 200.ms, duration: 400.ms),
                  const SizedBox(height: 20),

                  // ── Streak card ────────────────────────────────────────────
                  _StreakCard().animate().fadeIn(delay: 300.ms, duration: 400.ms),
                  const SizedBox(height: 20),

                  // ── Today's meals ──────────────────────────────────────────
                  _SectionHeader(
                    title: "Today's Meals",
                    action: TextButton(
                      onPressed: () => context.go('/log'),
                      child: const Text('See all', style: TextStyle(color: AppColors.emerald, fontSize: 13)),
                    ),
                  ),
                  const SizedBox(height: 12),
                  foodAsync.when(
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (_, __) => const SizedBox.shrink(),
                    data: (summary) => summary.logs.isEmpty
                        ? _EmptyMealsCard()
                        : Column(
                            children: summary.logs.take(4).map((log) => _MealRow(log: _FoodLogDisplay(
                              name: log.foodName,
                              calories: log.calories,
                              mealType: log.mealType.label,
                              confidence: log.confidenceLevel.value,
                            ))).toList(),
                          ),
                  ),
                ]),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _greeting() {
    final h = DateTime.now().hour;
    if (h < 12) return 'morning';
    if (h < 17) return 'afternoon';
    return 'evening';
  }
}

// ── Sub-widgets ───────────────────────────────────────────────────────────────

class _CalorieCard extends StatelessWidget {
  const _CalorieCard({
    required this.summary,
    required this.targetCalories,
    required this.totalBurned,
  });
  final dynamic summary;
  final double targetCalories;
  final double totalBurned;

  @override
  Widget build(BuildContext context) {
    final consumed = summary.totalCalories as double;
    // Net = consumed - burned (positive = surplus, negative = deficit)
    final net = consumed - totalBurned;
    final progress = (consumed / targetCalories).clamp(0.0, 1.0);
    final remaining = (targetCalories - consumed).clamp(0.0, double.infinity);

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
            children: [
              ProgressRing(
                progress: progress,
                size: 100,
                strokeWidth: 8,
                color: AppColors.emerald,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      consumed.toInt().toString(),
                      style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                    ),
                    const Text('kcal', style: TextStyle(fontSize: 10, color: AppColors.textMuted)),
                  ],
                ),
              ),
              const SizedBox(width: 20),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _CalorieStat('Goal', '${targetCalories.toInt()} kcal'),
                    const SizedBox(height: 6),
                    _CalorieStat('Consumed', '${consumed.toInt()} kcal'),
                    const SizedBox(height: 6),
                    _CalorieStat('Remaining', '${remaining.toInt()} kcal',
                        color: remaining < 200 ? AppColors.amber : AppColors.emerald),
                  ],
                ),
              ),
            ],
          ),
          // Burned row
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: AppColors.surfaceElevated,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.local_fire_department_rounded,
                        color: AppColors.amber, size: 14),
                    const SizedBox(width: 6),
                    Text('Burned ${totalBurned.toInt()} kcal',
                        style: const TextStyle(
                            color: AppColors.textSecondary, fontSize: 12)),
                  ],
                ),
                Row(
                  children: [
                    Text(
                      net >= 0
                          ? '+${net.toInt()} surplus'
                          : '${net.toInt().abs()} deficit',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: net >= 0 ? AppColors.amber : AppColors.emerald,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

}

class _CalorieStat extends StatelessWidget {
  const _CalorieStat(this.label, this.value, {this.color});
  final String label;
  final String value;
  final Color? color;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
          Text(value,
              style: TextStyle(
                  color: color ?? AppColors.textPrimary,
                  fontSize: 13,
                  fontWeight: FontWeight.w600)),
        ],
      );
}

class _MacroRow extends StatelessWidget {
  const _MacroRow({
    required this.proteinG,
    required this.carbsG,
    required this.fatG,
    required this.proteinTarget,
    required this.carbsTarget,
    required this.fatTarget,
  });
  final double proteinG, carbsG, fatG;
  final double proteinTarget, carbsTarget, fatTarget;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(child: _MacroChip('Protein', proteinG, proteinTarget, AppColors.blue)),
          const SizedBox(width: 8),
          Expanded(child: _MacroChip('Carbs', carbsG, carbsTarget, AppColors.amber)),
          const SizedBox(width: 8),
          Expanded(child: _MacroChip('Fat', fatG, fatTarget, AppColors.purple)),
        ],
      );
}

class _MacroChip extends StatelessWidget {
  const _MacroChip(this.label, this.current, this.target, this.color);
  final String label;
  final double current, target;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final progress = (current / target).clamp(0.0, 1.0);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
          const SizedBox(height: 4),
          Text(
            '${current.toInt()}g',
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: progress,
              backgroundColor: color.withAlpha(51),
              valueColor: AlwaysStoppedAnimation(color),
              minHeight: 4,
            ),
          ),
          const SizedBox(height: 2),
          Text('/ ${target.toInt()}g', style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
        ],
      ),
    );
  }
}

class _StreakCard extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return FutureBuilder<StreakInfo>(
      future: AnalyticsApi.getStreak(),
      builder: (context, snap) {
        final streak = snap.data;
        return Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.border),
          ),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: AppColors.amber.withAlpha(26),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.local_fire_department_rounded, color: AppColors.amber, size: 28),
              ),
              const SizedBox(width: 16),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${streak?.currentStreakDays ?? 0} day streak',
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  Text(
                    streak?.isActiveToday == true ? 'Logged today ✓' : 'Log today to keep it going!',
                    style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

class _QuickAction extends StatelessWidget {
  const _QuickAction({required this.icon, required this.label, required this.color, required this.onTap});
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 16),
          decoration: BoxDecoration(
            color: color.withAlpha(26),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: color.withAlpha(51)),
          ),
          child: Column(
            children: [
              Icon(icon, color: color, size: 28),
              const SizedBox(height: 6),
              Text(label, style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.w500)),
            ],
          ),
        ),
      );
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title, this.action});
  final String title;
  final Widget? action;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          if (action != null) action!,
        ],
      );
}

// Simple display model to avoid importing food_log in nested widget
class _FoodLogDisplay {
  const _FoodLogDisplay({required this.name, required this.calories, required this.mealType, required this.confidence});
  final String name;
  final double calories;
  final String mealType;
  final String confidence;
}

class _MealRow extends StatelessWidget {
  const _MealRow({required this.log});
  final _FoodLogDisplay log;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
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
                  Text(log.name, style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 14)),
                  Text(log.mealType, style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                ],
              ),
            ),
            Text(
              '${log.calories.toInt()} kcal',
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
            ),
          ],
        ),
      );
}

class _EmptyMealsCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: const Center(
          child: Text(
            'No meals logged yet today.\nTap Log Food to get started.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.textMuted, fontSize: 14),
          ),
        ),
      );
}

class _CalorieCardSkeleton extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
        height: 140,
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.border),
        ),
      );
}

class _ErrorCard extends StatelessWidget {
  const _ErrorCard({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.red.withAlpha(26),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.red.withAlpha(51)),
        ),
        child: Text(message, style: const TextStyle(color: AppColors.red, fontSize: 13)),
      );
}
