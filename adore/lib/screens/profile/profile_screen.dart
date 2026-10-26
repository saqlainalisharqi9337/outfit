import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../models/product_model.dart';
import '../../models/user_model.dart';
import '../../providers/auth_provider.dart';
import '../../providers/shop_provider.dart';
import '../../providers/theme_controller.dart';
import '../../services/feedback_service.dart';
import '../../services/storage_service.dart';
import '../../theme/app_theme.dart';
import '../../utils/enums.dart';
import '../../utils/exceptions.dart';
import '../../utils/photo_picker.dart';
import '../../widgets/common.dart';
import '../shop/orders_screen.dart';
import 'edit_profile_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  bool _uploading = false;
  late Future<List<OutfitFeedback>> _history;

  static const _styles = [
    'Casual',
    'Elegant',
    'Sporty',
    'Bohemian',
    'Minimalist',
    'Streetwear',
    'Business',
    'Romantic',
    'Edgy',
    'Classic',
  ];
  static const _clothingSizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];
  static const _braSizes = [
    '30A', '30B', '30C', '32A', '32B', '32C', '34A', '34B', '34C', '34D', '36B', '36C', '36D',
  ];

  @override
  void initState() {
    super.initState();
    final uid = context.read<AuthProvider>().profile?.id;
    _history = uid == null ? Future.value(const []) : FeedbackService().list(uid);
    if (uid != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) context.read<ShopProvider>().loadOrders(uid);
      });
    }
  }

  Future<void> _save(UserModel next) async {
    await context.read<AuthProvider>().saveProfile(next);
  }

  Future<void> _changePhoto() async {
    final auth = context.read<AuthProvider>();
    final user = auth.profile;
    if (user == null || _uploading) return;
    try {
      final bytes = await PhotoPicker.pickWithSheet(context, selfie: true);
      if (bytes == null || !mounted) return;
      setState(() => _uploading = true);
      final url = await context.read<StorageService>().uploadProfileImage(
            uid: user.id,
            bytes: bytes,
          );
      await auth.saveProfile(user.copyWith(profileImageUrl: url));
    } on AppException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not update the photo. Try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final theme = context.watch<ThemeController>();
    final shop = context.watch<ShopProvider>();
    final user = auth.profile;
    if (user == null) return const LoadingView();
    final dark = Theme.of(context).brightness == Brightness.dark;
    final ink = dark ? AppColors.darkInk : AppColors.ink;
    final muted = dark ? AppColors.darkMuted : AppColors.muted;
    final card = dark ? AppColors.darkSurface : AppColors.surface;
    final styles = user.preferences.preferredStyles;
    final isFemale = user.gender == Gender.female;
    final sizeLabel = [
      user.preferences.clothingSize,
      if (isFemale) user.preferences.braSize,
    ].whereType<String>().where((v) => v.isNotEmpty).join(' · ');

    ImageProvider? avatar;
    final url = user.profileImageUrl;
    if (url != null && url.isNotEmpty) {
      avatar = url.startsWith('data:')
          ? MemoryImage(base64Decode(url.split(',').last))
          : NetworkImage(url);
    }

    return Scaffold(
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
        children: [
          Row(
            children: [
              Text('Profile', style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: ink)),
              const Spacer(),
              IconButton(
                tooltip: 'Inbox',
                onPressed: () => _inbox(context),
                icon: Icon(Icons.chat_bubble_outline, color: muted),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              GestureDetector(
                onTap: _uploading ? null : _changePhoto,
                child: CircleAvatar(
                  radius: 36,
                  backgroundColor: AppColors.primary,
                  backgroundImage: avatar,
                  child: avatar == null
                      ? const Icon(Icons.person, color: Colors.white, size: 36)
                      : null,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(user.name, style: TextStyle(color: ink, fontSize: 20, fontWeight: FontWeight.w600)),
                    Text(user.email, style: TextStyle(color: muted, fontSize: 13)),
                    TextButton(
                      onPressed: () => _editName(user),
                      style: TextButton.styleFrom(
                        padding: EdgeInsets.zero,
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        foregroundColor: AppColors.primary,
                      ),
                      child: const Text('Edit Profile'),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 22),
          _section('Account overview', muted),
          _card(card, [
            _row(
              ink: ink,
              muted: muted,
              icon: Icons.person_outline,
              iconBg: AppColors.primary.withValues(alpha: 0.12),
              iconColor: AppColors.primary,
              title: 'Gender',
              subtitle: 'Tailors silhouettes & sizing',
              value: user.gender?.label ?? 'Not set',
              valueColor: AppColors.primary,
              onTap: () => _pickGender(user),
            ),
            _row(
              ink: ink,
              muted: muted,
              icon: Icons.checkroom_outlined,
              iconBg: AppColors.primary.withValues(alpha: 0.12),
              iconColor: AppColors.primary,
              title: 'Body Type',
              subtitle: 'Personalized fit',
              value: _bodyLabel(user.bodyType),
              valueColor: AppColors.primary,
              onTap: () => _pickBody(user),
            ),
            _row(
              ink: ink,
              muted: muted,
              icon: Icons.straighten,
              iconBg: AppColors.secondary.withValues(alpha: 0.12),
              iconColor: AppColors.secondary,
              title: 'Size',
              subtitle: isFemale ? 'Clothing & bra size' : 'Clothing size',
              value: sizeLabel.isEmpty ? 'Not set' : sizeLabel,
              valueColor: AppColors.secondary,
              onTap: () => _pickSize(user),
              last: true,
            ),
          ]),
          const SizedBox(height: 18),
          _section('Appearance', muted),
          _card(card, [
            SwitchListTile(
              secondary: CircleAvatar(
                backgroundColor: dark ? const Color(0xFF312E81) : const Color(0xFFE0E7FF),
                child: Icon(dark ? Icons.dark_mode : Icons.light_mode, color: dark ? const Color(0xFFA5B4FC) : const Color(0xFFF5A623)),
              ),
              title: Text(dark ? 'Dark Mode' : 'Light Mode', style: TextStyle(color: ink, fontSize: 14)),
              subtitle: Text(dark ? 'Switch to light theme' : 'Switch to dark theme', style: TextStyle(color: muted, fontSize: 12)),
              value: theme.isDark,
              activeThumbColor: Colors.white,
              activeTrackColor: const Color(0xFF6366F1),
              onChanged: (value) => theme.setDark(value),
            ),
          ]),
          const SizedBox(height: 18),
          _section('Style & preferences', muted),
          _card(card, [
            _row(
              ink: ink,
              muted: muted,
              icon: Icons.bar_chart,
              iconBg: const Color(0xFFDBEAFE),
              iconColor: const Color(0xFF3B82F6),
              title: 'Outfit History',
              subtitle: 'View past outfit picks',
              onTap: () => _showHistory(ink, muted, card),
            ),
            _row(
              ink: ink,
              muted: muted,
              icon: Icons.favorite_border,
              iconBg: const Color(0xFFFCE7F3),
              iconColor: const Color(0xFFEC4899),
              title: 'Favourite Style',
              subtitle: styles.isEmpty ? 'Not set' : styles.join(', '),
              onTap: () => _pickStyles(user),
              last: true,
            ),
          ]),
          const SizedBox(height: 12),
          _card(card, [
            _row(
              ink: ink,
              muted: muted,
              icon: Icons.tune,
              iconBg: AppColors.secondary.withValues(alpha: 0.12),
              iconColor: AppColors.secondary,
              title: 'More Recommendation',
              subtitle: 'Culture, colors, and fit preferences',
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const EditProfileScreen()),
              ),
              last: true,
            ),
          ]),
          const SizedBox(height: 18),
          _section('Orders', muted),
          _card(card, [
            _row(
              ink: ink,
              muted: muted,
              icon: Icons.inventory_2_outlined,
              iconBg: const Color(0xFFFFEDD5),
              iconColor: const Color(0xFFF97316),
              title: 'Your Orders',
              subtitle: 'Track & manage orders',
              badge: '${shop.orders.length}',
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const OrdersScreen())),
            ),
            _row(
              ink: ink,
              muted: muted,
              icon: Icons.inbox_outlined,
              iconBg: const Color(0xFFCCFBF1),
              iconColor: const Color(0xFF14B8A6),
              title: 'Inbox & FAQ',
              subtitle: 'Messages & common questions',
              onTap: () => _inbox(context),
              last: true,
            ),
          ]),
          const SizedBox(height: 18),
          _section('Help', muted),
          _card(card, [
            _row(
              ink: ink,
              muted: muted,
              icon: Icons.help_outline,
              iconBg: AppColors.secondary.withValues(alpha: 0.15),
              iconColor: AppColors.secondary,
              title: 'Support & More',
              subtitle: 'Contact us, rate the app',
              onTap: () => _support(ink, muted, card),
              last: true,
            ),
          ]),
          const SizedBox(height: 18),
          DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              gradient: const LinearGradient(colors: [AppColors.primary, AppColors.secondary]),
            ),
            child: TextButton.icon(
              onPressed: () => auth.logout(),
              icon: const Icon(Icons.logout, color: Colors.white),
              label: const Text('Logout', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
            ),
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: () => _deleteInfo(context),
            icon: const Icon(Icons.delete_outline, color: AppColors.danger),
            label: const Text('Delete Account', style: TextStyle(color: AppColors.danger)),
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }

  Widget _section(String title, Color muted) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 8),
      child: Text(title.toUpperCase(), style: TextStyle(color: muted, fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 0.6)),
    );
  }

  Widget _card(Color color, List<Widget> children) {
    return DecoratedBox(
      decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(18)),
      child: Column(children: children),
    );
  }

  Widget _row({
    required Color ink,
    required Color muted,
    required IconData icon,
    required Color iconBg,
    required Color iconColor,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    String? value,
    Color? valueColor,
    String? badge,
    bool last = false,
  }) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          border: last ? null : Border(bottom: BorderSide(color: muted.withValues(alpha: 0.15))),
        ),
        child: Row(
          children: [
            CircleAvatar(backgroundColor: iconBg, child: Icon(icon, color: iconColor, size: 20)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: TextStyle(color: ink, fontWeight: FontWeight.w600)),
                  Text(subtitle, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: muted, fontSize: 12)),
                ],
              ),
            ),
            if (badge != null)
              Container(
                margin: const EdgeInsets.only(right: 6),
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(color: const Color(0xFFFFEDD5), borderRadius: BorderRadius.circular(20)),
                child: Text(badge, style: const TextStyle(color: Color(0xFFEA580C), fontSize: 12)),
              ),
            if (value != null)
              Flexible(
                child: Text(value, overflow: TextOverflow.ellipsis, style: TextStyle(color: valueColor, fontWeight: FontWeight.w600)),
              ),
            Icon(Icons.chevron_right, color: muted, size: 18),
          ],
        ),
      ),
    );
  }

  String _bodyLabel(BodyType? type) => switch (type) {
        BodyType.rectangle => 'Rectangle',
        BodyType.pear => 'Pear-shaped',
        BodyType.apple => 'Apple',
        BodyType.hourglass => 'Hourglass',
        BodyType.invertedTriangle => 'Inverted Triangle',
        null => 'Not set',
      };

  Future<void> _pickBody(UserModel user) async {
    var selected = user.bodyType;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheet) {
            return Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('Body Type', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  const Text('Choose your body type to get better-fitted outfit suggestions.'),
                  const SizedBox(height: 12),
                  for (final type in BodyType.values)
                    ListTile(
                      title: Text(_bodyLabel(type)),
                      trailing: selected == type ? const Icon(Icons.check, color: AppColors.primary) : null,
                      onTap: () => setSheet(() => selected = type),
                    ),
                  FilledButton(
                    onPressed: selected == null
                        ? null
                        : () async {
                            await _save(user.copyWith(bodyType: selected));
                            if (context.mounted) Navigator.pop(context);
                          },
                    child: const Text('Save Body Type'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _pickGender(UserModel user) async {
    var selected = user.gender;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheet) {
            return Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('Gender', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  const Text('Choose your gender to tailor outfit silhouettes and sizing.'),
                  const SizedBox(height: 12),
                  for (final g in Gender.values)
                    ListTile(
                      title: Text(g.label),
                      trailing: selected == g ? const Icon(Icons.check, color: AppColors.primary) : null,
                      onTap: () => setSheet(() => selected = g),
                    ),
                  const SizedBox(height: 8),
                  FilledButton(
                    onPressed: selected == null
                        ? null
                        : () async {
                            final willBeMale = selected == Gender.male;
                            await _save(
                              user.copyWith(
                                gender: selected,
                                preferences: willBeMale
                                    ? user.preferences.copyWith(clearBraSize: true)
                                    : user.preferences,
                              ),
                            );
                            if (context.mounted) Navigator.pop(context);
                          },
                    child: const Text('Save Gender'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _pickSize(UserModel user) async {
    final isFemale = user.gender == Gender.female;
    var clothing = user.preferences.clothingSize ?? 'M';
    var bra = isFemale ? (user.preferences.braSize ?? '30C') : null;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheet) {
            return Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('Your Size', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 12),
                  const Text('Clothing Size'),
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final size in _clothingSizes)
                        ChoiceChip(
                          label: Text(size),
                          selected: clothing == size,
                          onSelected: (_) => setSheet(() => clothing = size),
                        ),
                    ],
                  ),
                  if (isFemale) ...[
                    const SizedBox(height: 12),
                    const Text('Bra Size'),
                    Wrap(
                      spacing: 8,
                      children: [
                        for (final size in _braSizes)
                          ChoiceChip(
                            label: Text(size),
                            selected: bra == size,
                            onSelected: (_) => setSheet(() => bra = size),
                          ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: () async {
                      await _save(
                        user.copyWith(
                          preferences: user.preferences.copyWith(
                            clothingSize: clothing,
                            braSize: isFemale ? bra : null,
                            clearBraSize: !isFemale,
                          ),
                        ),
                      );
                      if (context.mounted) Navigator.pop(context);
                    },
                    child: const Text('Save Sizes'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _pickStyles(UserModel user) async {
    final selected = {...user.preferences.preferredStyles};
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheet) {
            return Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('Favorite Styles', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  const Text('These styles are saved on your account and used for outfit suggestions.'),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final style in _styles)
                        FilterChip(
                          label: Text(style),
                          selected: selected.contains(style),
                          onSelected: (on) => setSheet(() {
                            if (on) {
                              selected.add(style);
                            } else {
                              selected.remove(style);
                            }
                          }),
                        ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: selected.isEmpty
                        ? null
                        : () async {
                            await _save(
                              user.copyWith(
                                preferences: user.preferences.copyWith(preferredStyles: selected.toList()),
                              ),
                            );
                            if (context.mounted) Navigator.pop(context);
                          },
                    child: const Text('Save Preferences'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _editName(UserModel user) async {
    final name = TextEditingController(text: user.name);
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) {
        return Padding(
          padding: EdgeInsets.fromLTRB(20, 0, 20, 24 + MediaQuery.viewInsetsOf(context).bottom),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text('Edit Profile', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
              const SizedBox(height: 12),
              TextField(controller: name, decoration: const InputDecoration(labelText: 'Full name')),
              const SizedBox(height: 8),
              TextField(
                enabled: false,
                decoration: InputDecoration(labelText: 'Email', hintText: user.email),
              ),
              const SizedBox(height: 12),
              FilledButton(
                onPressed: () async {
                  final next = name.text.trim();
                  if (next.isEmpty) return;
                  await _save(user.copyWith(name: next));
                  if (context.mounted) Navigator.pop(context);
                },
                child: const Text('Save Changes'),
              ),
            ],
          ),
        );
      },
    );
    name.dispose();
  }

  Future<void> _showHistory(Color ink, Color muted, Color card) async {
    final rows = await _history;
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text('Outfit History', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
              const SizedBox(height: 12),
              if (rows.isEmpty)
                const Text('No saved outfit picks yet. Like or save a look on the Outfit screen.')
              else
                for (final row in rows.take(8))
                  ListTile(
                    tileColor: card,
                    title: Text(row.subcategories.isEmpty ? row.type.name : row.subcategories.join(', '), style: TextStyle(color: ink)),
                    subtitle: Text(DateFormat.MMMd().add_jm().format(row.createdAt), style: TextStyle(color: muted)),
                  ),
            ],
          ),
        );
      },
    );
  }

  void _inbox(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => const Padding(
        padding: EdgeInsets.fromLTRB(20, 0, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Inbox & FAQ', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            SizedBox(height: 12),
            Text('No new messages. Order and style updates appear with your account.'),
            SizedBox(height: 12),
            Text('How do outfit suggestions work?'),
            Text('They use your body type, size, favorite styles, wardrobe, and live weather.'),
            SizedBox(height: 8),
            Text('How do I update my measurements?'),
            Text('Profile → Body Type or Size. Those values are saved on your account.'),
          ],
        ),
      ),
    );
  }

  void _support(Color ink, Color muted, Color card) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Support & More', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            ListTile(
              tileColor: card,
              title: Text('Email support', style: TextStyle(color: ink)),
              subtitle: Text('Use the address on your Adore project account.', style: TextStyle(color: muted)),
            ),
            const SizedBox(height: 8),
            Text('Adore v1.0.0', style: TextStyle(color: muted, fontSize: 12)),
          ],
        ),
      ),
    );
  }

  void _deleteInfo(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Account'),
        content: const Text(
          'This app does not delete Supabase accounts. Your wardrobe and profile stay on the server. You can log out from this device.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close')),
        ],
      ),
    );
  }
}
