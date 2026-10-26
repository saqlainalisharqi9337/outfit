import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../models/outfit_model.dart';
import '../theme/app_theme.dart';
import '../utils/enums.dart';
import 'common.dart';
import 'motion.dart';

class OutfitCard extends StatelessWidget {
  const OutfitCard({
    super.key,
    required this.outfit,
    this.onTap,
    this.compact = false,
  });

  final OutfitRecommendation outfit;
  final VoidCallback? onTap;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return PressableScale(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.xl),
          border: Border.all(color: AppColors.cardBorder),
          boxShadow: AppShadows.soft,
        ),
        child: Padding(
          padding: const EdgeInsets.all(AppSpace.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      outfit.title,
                      style: GoogleFonts.playfairDisplay(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.primarySoft,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      '${outfit.breakdown.percent}%',
                      style: const TextStyle(
                        color: AppColors.primary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              SizedBox(
                height: compact ? 102 : 140,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: [
                    for (final slot in outfit.slots)
                      Padding(
                        padding: const EdgeInsets.only(right: 10),
                        child: Column(
                          children: [
                            DecoratedBox(
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(16),
                                boxShadow: AppShadows.soft,
                              ),
                              child: NetworkImageView(
                                url: slot.item?.imageUrl ??
                                    slot.missingSuggestion?.matchedProduct
                                        ?.imageUrl ??
                                    '',
                                height: compact ? 72 : 104,
                                width: compact ? 72 : 104,
                                fit: BoxFit.contain,
                                openOnTap: true,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              slot.item?.subcategory ??
                                  slot.missingSuggestion?.subcategory ??
                                  slot.category.label,
                              style: const TextStyle(
                                fontSize: 11,
                                color: AppColors.muted,
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
              if (!outfit.fromWardrobe)
                const Padding(
                  padding: EdgeInsets.only(top: 8),
                  child: Text(
                    'Includes new clothing recommendations',
                    style: TextStyle(color: AppColors.warning, fontSize: 12),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
