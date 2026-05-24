import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';

class TrackLogo extends StatelessWidget {
  const TrackLogo({super.key});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [AppColors.emeraldLight, AppColors.emeraldDark],
            ),
            borderRadius: BorderRadius.circular(10),
            boxShadow: [
              BoxShadow(
                color: AppColors.emerald.withAlpha(76),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: const Icon(Icons.bolt_rounded, color: Colors.white, size: 20),
        ),
        const SizedBox(width: 10),
        const Text(
          'Track',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, letterSpacing: -0.5),
        ),
      ],
    );
  }
}
