import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:uuid/uuid.dart';

import '../models/product_model.dart';
import '../utils/enums.dart';
import '../utils/exceptions.dart';
import '../utils/json_helpers.dart';
import 'demo_store.dart';

class ShoppingService {
  ShoppingService({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  final SupabaseClient _client;
  final _uuid = const Uuid();
  List<ProductModel>? _bundled;

  static const Map<String, String> _urlReplacements = {
    '1594938291221': 'https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?auto=format&fit=crop&w=800&q=80',
    '1520975954732': 'https://images.unsplash.com/photo-1601924994987-69e26d50dc26?auto=format&fit=crop&w=800&q=80',
    '1608256246200': 'https://images.unsplash.com/photo-1520639888713-7851133b1ed0?auto=format&fit=crop&w=800&q=80',
    '1520903920243': 'https://images.unsplash.com/photo-1520903920243-00d872a2d1c9?auto=format&fit=crop&w=800&q=80',
    '1503341455253': 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=800&q=80',
  };

  static String sanitizeUrl(String? id, String? rawUrl, [String? fallback]) {
    if (rawUrl == null || rawUrl.isEmpty) {
      return fallback ?? '';
    }
    for (final entry in _urlReplacements.entries) {
      if (rawUrl.contains(entry.key)) {
        return fallback ?? entry.value;
      }
    }
    return rawUrl;
  }

  Future<List<ProductModel>> loadProducts() async {
    final bundled = await _loadBundled();
    if (DemoStore.instance.active) {
      return bundled;
    }
    try {
      final rows = await _client.from('products').select();
      if (rows.isNotEmpty) {
        final bundledMap = {for (final b in bundled) b.id: b};
        final existingIds = <String>{};
        final list = <ProductModel>[];
        for (final row in rows) {
          final id = row['id'] as String;
          existingIds.add(id);
          final map = Map<String, dynamic>.from(row);
          final rawUrl = (map['image_url'] ?? map['imageUrl']) as String?;
          final cleanUrl = sanitizeUrl(id, rawUrl, bundledMap[id]?.imageUrl);
          if (cleanUrl != rawUrl && cleanUrl.isNotEmpty) {
            map['image_url'] = cleanUrl;
            map['imageUrl'] = cleanUrl;
            _client
                .from('products')
                .update({'image_url': cleanUrl})
                .eq('id', id)
                .catchError((_) {});
          }
          list.add(ProductModel.fromMap(id, map));
        }
        for (final b in bundled) {
          if (!existingIds.contains(b.id)) {
            list.add(b);
          }
        }
        return list;
      }
    } catch (_) {}
    return bundled;
  }

  Future<List<ProductModel>> _loadBundled() async {
    if (_bundled != null) return _bundled!;
    final raw = await rootBundle.loadString('assets/data/products.json');
    final list = jsonDecode(raw) as List<dynamic>;
    _bundled = list
        .map((e) => ProductModel.fromMap(
              (e as Map<String, dynamic>)['id'] as String,
              e,
            ))
        .toList();
    return _bundled!;
  }

  Future<List<ProductModel>> search({
    String query = '',
    ClothingCategory? category,
    String? color,
  }) async {
    final all = await loadProducts();
    final q = query.trim().toLowerCase();
    return all.where((p) {
      final matchesQuery = q.isEmpty ||
          p.name.toLowerCase().contains(q) ||
          p.subcategory.toLowerCase().contains(q) ||
          p.description.toLowerCase().contains(q);
      final matchesCategory = category == null || p.category == category;
      final matchesColor = color == null || p.color == color;
      return matchesQuery && matchesCategory && matchesColor;
    }).toList();
  }

  Future<ProductModel?> byId(String id) async {
    final all = await loadProducts();
    for (final p in all) {
      if (p.id == id) return p;
    }
    return null;
  }

  Stream<List<CartItem>> watchCart(String uid) {
    if (DemoStore.instance.active) {
      return DemoStore.instance.watchCart();
    }
    return _client
        .from('cart_items')
        .stream(primaryKey: ['id'])
        .eq('user_id', uid)
        .asyncMap((rows) async {
          final products = await loadProducts();
          return rows.map((row) {
            final data = Map<String, dynamic>.from(row);
            final productId = pick(data, 'product_id', 'productId') as String? ?? '';
            final product = products.firstWhere(
              (p) => p.id == productId,
              orElse: () => ProductModel.fromMap(productId, {
                'name': pick(data, 'name'),
                'price': pick(data, 'price'),
                'imageUrl': pick(data, 'image_url', 'imageUrl'),
                'description': '',
                'category': 'upperwear',
                'subcategory': 'jacket',
                'color': 'black',
                'cultureTags': const [],
                'weatherBands': const [],
              }),
            );
            return CartItem(
              product: product,
              quantity: (pick(data, 'quantity') as num?)?.toInt() ?? 1,
            );
          }).toList();
        });
  }

  Future<void> addToCart(String uid, ProductModel product, {int quantity = 1}) async {
    if (DemoStore.instance.active) {
      final items = DemoStore.instance.cart;
      final index = items.indexWhere((e) => e.product.id == product.id);
      if (index >= 0) {
        items[index] = items[index].copyWith(
          quantity: items[index].quantity + quantity,
        );
      } else {
        items.add(CartItem(product: product, quantity: quantity));
      }
      DemoStore.instance.emitCart();
      return;
    }
    try {
      final existing = await _client
          .from('cart_items')
          .select()
          .eq('user_id', uid)
          .eq('product_id', product.id)
          .maybeSingle();
      final current = (existing?['quantity'] as num?)?.toInt() ?? 0;
      await _client.from('cart_items').upsert(
            {
              ...CartItem(product: product, quantity: current + quantity).toRow(uid),
              if (existing?['id'] != null) 'id': existing!['id'],
            },
            onConflict: 'user_id,product_id',
          );
    } catch (_) {
      throw DatabaseException('Could not add this item to your cart.');
    }
  }

  Future<void> updateQuantity(String uid, String productId, int quantity) async {
    if (DemoStore.instance.active) {
      if (quantity <= 0) {
        DemoStore.instance.cart.removeWhere((e) => e.product.id == productId);
      } else {
        final items = DemoStore.instance.cart;
        final index = items.indexWhere((e) => e.product.id == productId);
        if (index >= 0) {
          items[index] = items[index].copyWith(quantity: quantity);
        }
      }
      DemoStore.instance.emitCart();
      return;
    }
    if (quantity <= 0) {
      await _client
          .from('cart_items')
          .delete()
          .eq('user_id', uid)
          .eq('product_id', productId);
      return;
    }
    await _client
        .from('cart_items')
        .update({'quantity': quantity})
        .eq('user_id', uid)
        .eq('product_id', productId);
  }

  Future<void> clearCart(String uid) async {
    if (DemoStore.instance.active) {
      DemoStore.instance.cart.clear();
      DemoStore.instance.emitCart();
      return;
    }
    await _client.from('cart_items').delete().eq('user_id', uid);
  }

  Future<OrderModel> checkout({
    required String uid,
    required List<CartItem> items,
  }) async {
    if (items.isEmpty) {
      throw DatabaseException('Your cart is empty.');
    }
    final order = OrderModel(
      id: _uuid.v4(),
      userId: uid,
      items: items,
      total: items.fold(0, (running, i) => running + i.lineTotal),
      status: OrderStatus.demoCompleted,
      createdAt: DateTime.now(),
      note:
          'Simulated checkout for FYP demonstration. No real payment was processed.',
    );
    try {
      if (DemoStore.instance.active) {
        DemoStore.instance.orders.insert(0, order);
        await clearCart(uid);
        return order;
      }
      await _client.from('orders').insert(order.toRow());
      await clearCart(uid);
      return order;
    } catch (_) {
      throw DatabaseException('Could not place the demo order.');
    }
  }

  Future<List<OrderModel>> listOrders(String uid) async {
    if (DemoStore.instance.active) {
      return List.of(DemoStore.instance.orders);
    }
    final rows = await _client
        .from('orders')
        .select()
        .eq('user_id', uid)
        .order('created_at', ascending: false);
    return rows.map((row) {
      final data = Map<String, dynamic>.from(row);
      final items = (pick(data, 'items') as List<dynamic>? ?? []).map((raw) {
        final map = Map<String, dynamic>.from(raw as Map);
        return CartItem(
          product: ProductModel.fromMap(
            pick(map, 'product_id', 'productId') as String? ?? '',
            {
              'name': pick(map, 'name'),
              'price': pick(map, 'price'),
              'imageUrl': pick(map, 'image_url', 'imageUrl'),
              'description': '',
              'category': 'upperwear',
              'subcategory': 'item',
              'color': 'black',
              'cultureTags': const [],
              'weatherBands': const [],
            },
          ),
          quantity: (pick(map, 'quantity') as num?)?.toInt() ?? 1,
        );
      }).toList();
      return OrderModel(
        id: pick(data, 'id') as String,
        userId: uid,
        items: items,
        total: (pick(data, 'total') as num?)?.toDouble() ?? 0,
        status: enumFromString(
          OrderStatus.values,
          pick(data, 'status') as String?,
          OrderStatus.demoCompleted,
        ),
        createdAt: parseDate(pick(data, 'created_at', 'createdAt')) ?? DateTime.now(),
        note: pick(data, 'note') as String?,
      );
    }).toList();
  }
}
