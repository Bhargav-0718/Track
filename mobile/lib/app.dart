import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/theme/app_theme.dart';
import 'providers/auth_provider.dart';
import 'screens/auth/login_screen.dart';
import 'screens/auth/register_screen.dart';
import 'screens/home/home_screen.dart';
import 'screens/insights/insights_screen.dart';
import 'screens/log/log_screen.dart';
import 'screens/profile/profile_screen.dart';
import 'screens/progress/progress_screen.dart';
import 'widgets/app_shell.dart';

// ── Router ────────────────────────────────────────────────────────────────────
//
// IMPORTANT: The GoRouter must NOT be recreated on every auth state change.
// If the Provider watches authProvider directly and returns a new GoRouter each
// time, the entire navigation stack is torn down mid-request (e.g. while a
// login API call is in-flight), which disposes the login screen and causes
// "setState() called after dispose()".
//
// Solution: create the router once, and give it a refreshListenable that only
// fires when the user's actual auth status changes (logged in / logged out /
// initialization complete) — NOT on isLoading changes.

class _AuthChangeNotifier extends ChangeNotifier {
  _AuthChangeNotifier(Ref ref) {
    ref.listen<AuthState>(authProvider, (prev, next) {
      // Only refresh (re-run redirect) when the meaningful auth status changes
      final prevAuth = prev?.isAuthenticated ?? false;
      final prevInit = prev?.isInitialized ?? false;
      if (prevAuth != next.isAuthenticated || prevInit != next.isInitialized) {
        notifyListeners();
      }
    });
  }
}

final _routerProvider = Provider<GoRouter>((ref) {
  // Router is created once. Redirect reads auth state fresh via ref.read.
  final notifier = _AuthChangeNotifier(ref);

  return GoRouter(
    initialLocation: '/home',
    refreshListenable: notifier,
    redirect: (context, state) {
      // Read current auth state without watching (no rebuild, no recreation)
      final authState = ref.read(authProvider);

      if (!authState.isInitialized) return '/splash';

      final isAuth = authState.isAuthenticated;
      final isAuthRoute = state.matchedLocation.startsWith('/login') ||
          state.matchedLocation.startsWith('/register');

      if (!isAuth && !isAuthRoute) return '/login';
      if (isAuth && isAuthRoute) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const _SplashScreen()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),

      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
          GoRoute(path: '/log', builder: (_, __) => const LogScreen()),
          GoRoute(path: '/progress', builder: (_, __) => const ProgressScreen()),
          GoRoute(path: '/insights', builder: (_, __) => const InsightsScreen()),
          GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
        ],
      ),
    ],
  );
});

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
}

// ── App ───────────────────────────────────────────────────────────────────────

class TrackApp extends ConsumerWidget {
  const TrackApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Router is stable — only read once, not watched
    final router = ref.read(_routerProvider);

    return MaterialApp.router(
      title: 'Track',
      theme: AppTheme.dark,
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}
