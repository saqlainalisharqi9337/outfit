import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../utils/constants.dart';

/// Brand mark used on splash, login, and other hero moments.
class AdoreLogo extends StatelessWidget {
  const AdoreLogo({
    super.key,
    this.size = 96,
    this.borderRadius = 22,
  });

  final double size;
  final double borderRadius;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(borderRadius),
        boxShadow: AppShadows.soft,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(borderRadius),
        child: Image.asset(
          AppConstants.appLogoAsset,
          width: size,
          height: size,
          fit: BoxFit.cover,
          filterQuality: FilterQuality.high,
          semanticLabel: '${AppConstants.appName} logo',
        ),
      ),
    );
  }
}
