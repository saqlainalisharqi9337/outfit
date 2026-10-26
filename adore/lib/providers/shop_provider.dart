import 'package:flutter/foundation.dart';

import '../models/product_model.dart';
import '../services/shopping_service.dart';
import '../services/trends_service.dart';
import '../utils/enums.dart';
import '../models/user_model.dart';

class ShopProvider extends ChangeNotifier {
  ShopProvider({
    required ShoppingService shoppingService,
    required TrendsService trendsService,
  })  : _shoppingService = shoppingService,
        _trendsService = trendsService;

  final ShoppingService _shoppingService;
  final TrendsService _trendsService;

  List<ProductModel> products = [];
  List<CartItem> cart = [];
  List<TrendModel> trends = [];
  List<OrderModel> orders = [];
  bool loading = false;
  String? error;
  String query = '';
  ClothingCategory? category;

  Future<void> loadCatalog(UserModel? user) async {
    loading = true;
    notifyListeners();
    try {
      products = await _shoppingService.search(query: query, category: category);
      final allTrends = await _trendsService.loadTrends();
      trends = user == null ? allTrends : _trendsService.forUser(allTrends, user);
      error = null;
    } catch (e) {
      error = 'Could not load the shop catalog.';
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  void bindCart(String uid) {
    _shoppingService.watchCart(uid).listen((items) {
      cart = items;
      notifyListeners();
    });
  }

  Future<void> addToCart(String uid, ProductModel product) {
    return _shoppingService.addToCart(uid, product);
  }

  Future<void> setQuantity(String uid, String productId, int quantity) {
    return _shoppingService.updateQuantity(uid, productId, quantity);
  }

  double get cartTotal =>
      cart.fold(0, (sum, item) => sum + item.lineTotal);

  Future<OrderModel> checkout(String uid) async {
    final order = await _shoppingService.checkout(uid: uid, items: cart);
    orders.insert(0, order);
    notifyListeners();
    return order;
  }

  Future<void> loadOrders(String uid) async {
    orders = await _shoppingService.listOrders(uid);
    notifyListeners();
  }

  Future<void> applyFilters({
    String? query,
    ClothingCategory? category,
    bool clearCategory = false,
  }) async {
    if (query != null) this.query = query;
    if (clearCategory) {
      this.category = null;
    } else if (category != null) {
      this.category = category;
    }
    products = await _shoppingService.search(
      query: this.query,
      category: this.category,
    );
    notifyListeners();
  }
}
