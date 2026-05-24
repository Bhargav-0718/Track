import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/app_theme.dart';

// ── Bottom nav destinations ───────────────────────────────────────────────────

const _destinations = [
  _Destination('/home', 'Home', Icons.home_rounded, Icons.home_outlined),
  _Destination('/log', 'Log', Icons.add_circle_rounded, Icons.add_circle_outline_rounded),
  _Destination('/progress', 'Progress', Icons.photo_library_rounded, Icons.photo_library_outlined),
  _Destination('/insights', 'Insights', Icons.insights_rounded, Icons.insights_outlined),
  _Destination('/profile', 'Profile', Icons.person_rounded, Icons.person_outlined),
];

class _Destination {
  const _Destination(this.route, this.label, this.activeIcon, this.icon);
  final String route;
  final String label;
  final IconData activeIcon;
  final IconData icon;
}

// ── Shell ─────────────────────────────────────────────────────────────────────

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.child});
  final Widget child;

  int _indexFor(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    for (int i = 0; i < _destinations.length; i++) {
      if (location.startsWith(_destinations[i].route)) return i;
    }
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    final currentIndex = _indexFor(context);

    return Scaffold(
      body: child,
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: AppColors.border, width: 1)),
        ),
        child: BottomNavigationBar(
          currentIndex: currentIndex,
          onTap: (i) => context.go(_destinations[i].route),
          items: _destinations.map((d) {
            return BottomNavigationBarItem(
              icon: Icon(d.icon),
              activeIcon: Icon(d.activeIcon),
              label: d.label,
              backgroundColor: AppColors.surface,
            );
          }).toList(),
          backgroundColor: AppColors.surface,
          selectedItemColor: AppColors.emerald,
          unselectedItemColor: AppColors.textMuted,
          selectedFontSize: 11,
          unselectedFontSize: 11,
          type: BottomNavigationBarType.fixed,
          elevation: 0,
        ),
      ),
    );
  }
}
