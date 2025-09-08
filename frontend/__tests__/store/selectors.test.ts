/**
 * Store Selectors Test Suite
 * 40 comprehensive tests for store selector functions
 */

// Mock state interfaces
interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user' | 'guest';
  isActive: boolean;
  preferences: {
    theme: 'light' | 'dark';
    language: string;
    notifications: boolean;
  };
  createdAt: string;
}

interface Product {
  id: string;
  name: string;
  price: number;
  category: string;
  inStock: boolean;
  tags: string[];
  rating: number;
  reviewCount: number;
}

interface Order {
  id: string;
  userId: string;
  products: { productId: string; quantity: number; price: number }[];
  status: 'pending' | 'processing' | 'shipped' | 'delivered' | 'cancelled';
  total: number;
  createdAt: string;
}

interface AppState {
  users: {
    items: User[];
    loading: boolean;
    error: string | null;
    currentUserId: string | null;
  };
  products: {
    items: Product[];
    loading: boolean;
    error: string | null;
    filters: {
      category: string | null;
      priceRange: { min: number; max: number } | null;
      inStockOnly: boolean;
    };
  };
  orders: {
    items: Order[];
    loading: boolean;
    error: string | null;
  };
  ui: {
    theme: 'light' | 'dark';
    sidebarCollapsed: boolean;
    notifications: {
      id: string;
      type: 'success' | 'error' | 'warning' | 'info';
      message: string;
      timestamp: number;
    }[];
  };
}

// Selector functions
const selectors = {
  // User selectors
  getAllUsers: (state: AppState): User[] => state.users.items,
  
  getUsersLoading: (state: AppState): boolean => state.users.loading,
  
  getUsersError: (state: AppState): string | null => state.users.error,
  
  getCurrentUserId: (state: AppState): string | null => state.users.currentUserId,
  
  getCurrentUser: (state: AppState): User | null => {
    const userId = state.users.currentUserId;
    return userId ? state.users.items.find(user => user.id === userId) || null : null;
  },
  
  getUserById: (state: AppState, userId: string): User | null => {
    return state.users.items.find(user => user.id === userId) || null;
  },
  
  getActiveUsers: (state: AppState): User[] => {
    return state.users.items.filter(user => user.isActive);
  },
  
  getUsersByRole: (state: AppState, role: User['role']): User[] => {
    return state.users.items.filter(user => user.role === role);
  },
  
  getAdminUsers: (state: AppState): User[] => {
    return selectors.getUsersByRole(state, 'admin');
  },
  
  getUserCount: (state: AppState): number => state.users.items.length,
  
  getActiveUserCount: (state: AppState): number => {
    return selectors.getActiveUsers(state).length;
  },
  
  // Product selectors
  getAllProducts: (state: AppState): Product[] => state.products.items,
  
  getProductsLoading: (state: AppState): boolean => state.products.loading,
  
  getProductsError: (state: AppState): string | null => state.products.error,
  
  getProductById: (state: AppState, productId: string): Product | null => {
    return state.products.items.find(product => product.id === productId) || null;
  },
  
  getProductsByCategory: (state: AppState, category: string): Product[] => {
    return state.products.items.filter(product => product.category === category);
  },
  
  getInStockProducts: (state: AppState): Product[] => {
    return state.products.items.filter(product => product.inStock);
  },
  
  getProductsByPriceRange: (state: AppState, min: number, max: number): Product[] => {
    return state.products.items.filter(product => product.price >= min && product.price <= max);
  },
  
  getFilteredProducts: (state: AppState): Product[] => {
    let products = state.products.items;
    
    const { category, priceRange, inStockOnly } = state.products.filters;
    
    if (category) {
      products = products.filter(product => product.category === category);
    }
    
    if (priceRange) {
      products = products.filter(product => 
        product.price >= priceRange.min && product.price <= priceRange.max
      );
    }
    
    if (inStockOnly) {
      products = products.filter(product => product.inStock);
    }
    
    return products;
  },
  
  getTopRatedProducts: (state: AppState, limit: number = 10): Product[] => {
    return [...state.products.items]
      .sort((a, b) => b.rating - a.rating)
      .slice(0, limit);
  },
  
  getProductCategories: (state: AppState): string[] => {
    const categories = new Set(state.products.items.map(product => product.category));
    return Array.from(categories).sort();
  },
  
  getAverageProductPrice: (state: AppState): number => {
    const products = state.products.items;
    if (products.length === 0) return 0;
    const total = products.reduce((sum, product) => sum + product.price, 0);
    return total / products.length;
  },
  
  // Order selectors
  getAllOrders: (state: AppState): Order[] => state.orders.items,
  
  getOrdersLoading: (state: AppState): boolean => state.orders.loading,
  
  getOrdersError: (state: AppState): string | null => state.orders.error,
  
  getOrderById: (state: AppState, orderId: string): Order | null => {
    return state.orders.items.find(order => order.id === orderId) || null;
  },
  
  getOrdersByUserId: (state: AppState, userId: string): Order[] => {
    return state.orders.items.filter(order => order.userId === userId);
  },
  
  getCurrentUserOrders: (state: AppState): Order[] => {
    const currentUserId = state.users.currentUserId;
    return currentUserId ? selectors.getOrdersByUserId(state, currentUserId) : [];
  },
  
  getOrdersByStatus: (state: AppState, status: Order['status']): Order[] => {
    return state.orders.items.filter(order => order.status === status);
  },
  
  getPendingOrders: (state: AppState): Order[] => {
    return selectors.getOrdersByStatus(state, 'pending');
  },
  
  getTotalRevenue: (state: AppState): number => {
    return state.orders.items
      .filter(order => order.status === 'delivered')
      .reduce((total, order) => total + order.total, 0);
  },
  
  getOrderCount: (state: AppState): number => state.orders.items.length,
  
  getCompletedOrderCount: (state: AppState): number => {
    return state.orders.items.filter(order => order.status === 'delivered').length;
  },
  
  // UI selectors
  getTheme: (state: AppState): 'light' | 'dark' => state.ui.theme,
  
  isSidebarCollapsed: (state: AppState): boolean => state.ui.sidebarCollapsed,
  
  getNotifications: (state: AppState) => state.ui.notifications,
  
  getUnreadNotificationCount: (state: AppState): number => {
    return state.ui.notifications.length;
  },
  
  getNotificationsByType: (state: AppState, type: AppState['ui']['notifications'][0]['type']) => {
    return state.ui.notifications.filter(notification => notification.type === type);
  },
  
  getRecentNotifications: (state: AppState, limit: number = 5) => {
    return state.ui.notifications
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, limit);
  },
  
  // Complex composite selectors
  getUserOrderSummary: (state: AppState, userId: string) => {
    const orders = selectors.getOrdersByUserId(state, userId);
    return {
      totalOrders: orders.length,
      totalSpent: orders.reduce((sum, order) => sum + order.total, 0),
      pendingOrders: orders.filter(order => order.status === 'pending').length,
      completedOrders: orders.filter(order => order.status === 'delivered').length
    };
  },
  
  getDashboardStats: (state: AppState) => {
    return {
      totalUsers: selectors.getUserCount(state),
      activeUsers: selectors.getActiveUserCount(state),
      totalProducts: state.products.items.length,
      inStockProducts: selectors.getInStockProducts(state).length,
      totalOrders: selectors.getOrderCount(state),
      pendingOrders: selectors.getPendingOrders(state).length,
      totalRevenue: selectors.getTotalRevenue(state),
      averageOrderValue: selectors.getOrderCount(state) > 0 
        ? selectors.getTotalRevenue(state) / selectors.getCompletedOrderCount(state) 
        : 0
    };
  }
};

// Mock state data
const createMockState = (): AppState => ({
  users: {
    items: [
      {
        id: '1',
        name: 'John Doe',
        email: 'john@example.com',
        role: 'admin',
        isActive: true,
        preferences: { theme: 'dark', language: 'en', notifications: true },
        createdAt: '2024-01-15T10:00:00Z'
      },
      {
        id: '2',
        name: 'Jane Smith',
        email: 'jane@example.com',
        role: 'user',
        isActive: true,
        preferences: { theme: 'light', language: 'en', notifications: false },
        createdAt: '2024-01-16T10:00:00Z'
      },
      {
        id: '3',
        name: 'Bob Wilson',
        email: 'bob@example.com',
        role: 'user',
        isActive: false,
        preferences: { theme: 'light', language: 'es', notifications: true },
        createdAt: '2024-01-17T10:00:00Z'
      }
    ],
    loading: false,
    error: null,
    currentUserId: '1'
  },
  products: {
    items: [
      {
        id: 'p1',
        name: 'Laptop',
        price: 1200,
        category: 'Electronics',
        inStock: true,
        tags: ['computer', 'portable'],
        rating: 4.5,
        reviewCount: 150
      },
      {
        id: 'p2',
        name: 'Book',
        price: 25,
        category: 'Education',
        inStock: true,
        tags: ['reading', 'knowledge'],
        rating: 4.8,
        reviewCount: 89
      },
      {
        id: 'p3',
        name: 'Phone',
        price: 800,
        category: 'Electronics',
        inStock: false,
        tags: ['mobile', 'communication'],
        rating: 4.2,
        reviewCount: 203
      }
    ],
    loading: false,
    error: null,
    filters: {
      category: null,
      priceRange: null,
      inStockOnly: false
    }
  },
  orders: {
    items: [
      {
        id: 'o1',
        userId: '1',
        products: [{ productId: 'p1', quantity: 1, price: 1200 }],
        status: 'delivered',
        total: 1200,
        createdAt: '2024-01-20T10:00:00Z'
      },
      {
        id: 'o2',
        userId: '2',
        products: [{ productId: 'p2', quantity: 2, price: 25 }],
        status: 'pending',
        total: 50,
        createdAt: '2024-01-21T10:00:00Z'
      }
    ],
    loading: false,
    error: null
  },
  ui: {
    theme: 'light',
    sidebarCollapsed: false,
    notifications: [
      {
        id: 'n1',
        type: 'success',
        message: 'Order completed',
        timestamp: Date.now() - 1000
      },
      {
        id: 'n2',
        type: 'warning',
        message: 'Low stock alert',
        timestamp: Date.now() - 2000
      }
    ]
  }
});

describe('User Selectors', () => {
  const mockState = createMockState();

  test('should get all users', () => {
    const users = selectors.getAllUsers(mockState);
    expect(users).toHaveLength(3);
    expect(users[0].name).toBe('John Doe');
  });

  test('should get users loading state', () => {
    expect(selectors.getUsersLoading(mockState)).toBe(false);
  });

  test('should get users error', () => {
    expect(selectors.getUsersError(mockState)).toBeNull();
  });

  test('should get current user ID', () => {
    expect(selectors.getCurrentUserId(mockState)).toBe('1');
  });

  test('should get current user', () => {
    const currentUser = selectors.getCurrentUser(mockState);
    expect(currentUser?.name).toBe('John Doe');
  });

  test('should get user by ID', () => {
    const user = selectors.getUserById(mockState, '2');
    expect(user?.name).toBe('Jane Smith');
  });

  test('should return null for non-existent user ID', () => {
    const user = selectors.getUserById(mockState, 'nonexistent');
    expect(user).toBeNull();
  });

  test('should get active users', () => {
    const activeUsers = selectors.getActiveUsers(mockState);
    expect(activeUsers).toHaveLength(2);
    expect(activeUsers.every(user => user.isActive)).toBe(true);
  });

  test('should get users by role', () => {
    const adminUsers = selectors.getUsersByRole(mockState, 'admin');
    const regularUsers = selectors.getUsersByRole(mockState, 'user');
    
    expect(adminUsers).toHaveLength(1);
    expect(regularUsers).toHaveLength(2);
  });

  test('should get admin users', () => {
    const adminUsers = selectors.getAdminUsers(mockState);
    expect(adminUsers).toHaveLength(1);
    expect(adminUsers[0].role).toBe('admin');
  });

  test('should get user count', () => {
    expect(selectors.getUserCount(mockState)).toBe(3);
  });

  test('should get active user count', () => {
    expect(selectors.getActiveUserCount(mockState)).toBe(2);
  });
});

describe('Product Selectors', () => {
  const mockState = createMockState();

  test('should get all products', () => {
    const products = selectors.getAllProducts(mockState);
    expect(products).toHaveLength(3);
  });

  test('should get products loading state', () => {
    expect(selectors.getProductsLoading(mockState)).toBe(false);
  });

  test('should get products error', () => {
    expect(selectors.getProductsError(mockState)).toBeNull();
  });

  test('should get product by ID', () => {
    const product = selectors.getProductById(mockState, 'p1');
    expect(product?.name).toBe('Laptop');
  });

  test('should get products by category', () => {
    const electronics = selectors.getProductsByCategory(mockState, 'Electronics');
    expect(electronics).toHaveLength(2);
  });

  test('should get in-stock products', () => {
    const inStockProducts = selectors.getInStockProducts(mockState);
    expect(inStockProducts).toHaveLength(2);
    expect(inStockProducts.every(product => product.inStock)).toBe(true);
  });

  test('should get products by price range', () => {
    const affordableProducts = selectors.getProductsByPriceRange(mockState, 0, 100);
    expect(affordableProducts).toHaveLength(1);
    expect(affordableProducts[0].name).toBe('Book');
  });

  test('should get filtered products', () => {
    const stateWithFilters = {
      ...mockState,
      products: {
        ...mockState.products,
        filters: {
          category: 'Electronics',
          priceRange: null,
          inStockOnly: true
        }
      }
    };
    
    const filteredProducts = selectors.getFilteredProducts(stateWithFilters);
    expect(filteredProducts).toHaveLength(1);
    expect(filteredProducts[0].name).toBe('Laptop');
  });

  test('should get top rated products', () => {
    const topRated = selectors.getTopRatedProducts(mockState, 2);
    expect(topRated).toHaveLength(2);
    expect(topRated[0].rating).toBeGreaterThanOrEqual(topRated[1].rating);
  });

  test('should get product categories', () => {
    const categories = selectors.getProductCategories(mockState);
    expect(categories).toEqual(['Education', 'Electronics']);
  });

  test('should get average product price', () => {
    const averagePrice = selectors.getAverageProductPrice(mockState);
    expect(averagePrice).toBe((1200 + 25 + 800) / 3);
  });
});

describe('Order Selectors', () => {
  const mockState = createMockState();

  test('should get all orders', () => {
    const orders = selectors.getAllOrders(mockState);
    expect(orders).toHaveLength(2);
  });

  test('should get orders loading state', () => {
    expect(selectors.getOrdersLoading(mockState)).toBe(false);
  });

  test('should get orders error', () => {
    expect(selectors.getOrdersError(mockState)).toBeNull();
  });

  test('should get order by ID', () => {
    const order = selectors.getOrderById(mockState, 'o1');
    expect(order?.total).toBe(1200);
  });

  test('should get orders by user ID', () => {
    const userOrders = selectors.getOrdersByUserId(mockState, '1');
    expect(userOrders).toHaveLength(1);
  });

  test('should get current user orders', () => {
    const currentUserOrders = selectors.getCurrentUserOrders(mockState);
    expect(currentUserOrders).toHaveLength(1);
    expect(currentUserOrders[0].userId).toBe('1');
  });

  test('should get orders by status', () => {
    const pendingOrders = selectors.getOrdersByStatus(mockState, 'pending');
    const deliveredOrders = selectors.getOrdersByStatus(mockState, 'delivered');
    
    expect(pendingOrders).toHaveLength(1);
    expect(deliveredOrders).toHaveLength(1);
  });

  test('should get pending orders', () => {
    const pendingOrders = selectors.getPendingOrders(mockState);
    expect(pendingOrders).toHaveLength(1);
  });

  test('should get total revenue', () => {
    const revenue = selectors.getTotalRevenue(mockState);
    expect(revenue).toBe(1200); // Only delivered orders count
  });

  test('should get order count', () => {
    expect(selectors.getOrderCount(mockState)).toBe(2);
  });

  test('should get completed order count', () => {
    expect(selectors.getCompletedOrderCount(mockState)).toBe(1);
  });
});

describe('UI Selectors', () => {
  const mockState = createMockState();

  test('should get theme', () => {
    expect(selectors.getTheme(mockState)).toBe('light');
  });

  test('should get sidebar collapsed state', () => {
    expect(selectors.isSidebarCollapsed(mockState)).toBe(false);
  });

  test('should get notifications', () => {
    const notifications = selectors.getNotifications(mockState);
    expect(notifications).toHaveLength(2);
  });

  test('should get unread notification count', () => {
    expect(selectors.getUnreadNotificationCount(mockState)).toBe(2);
  });

  test('should get notifications by type', () => {
    const successNotifications = selectors.getNotificationsByType(mockState, 'success');
    const warningNotifications = selectors.getNotificationsByType(mockState, 'warning');
    
    expect(successNotifications).toHaveLength(1);
    expect(warningNotifications).toHaveLength(1);
  });

  test('should get recent notifications', () => {
    const recentNotifications = selectors.getRecentNotifications(mockState, 1);
    expect(recentNotifications).toHaveLength(1);
    expect(recentNotifications[0].message).toBe('Order completed');
  });
});

describe('Composite Selectors', () => {
  const mockState = createMockState();

  test('should get user order summary', () => {
    const summary = selectors.getUserOrderSummary(mockState, '1');
    expect(summary).toEqual({
      totalOrders: 1,
      totalSpent: 1200,
      pendingOrders: 0,
      completedOrders: 1
    });
  });

  test('should get dashboard stats', () => {
    const stats = selectors.getDashboardStats(mockState);
    expect(stats).toEqual({
      totalUsers: 3,
      activeUsers: 2,
      totalProducts: 3,
      inStockProducts: 2,
      totalOrders: 2,
      pendingOrders: 1,
      totalRevenue: 1200,
      averageOrderValue: 1200
    });
  });

  test('should handle empty state gracefully', () => {
    const emptyState: AppState = {
      users: { items: [], loading: false, error: null, currentUserId: null },
      products: { items: [], loading: false, error: null, filters: { category: null, priceRange: null, inStockOnly: false } },
      orders: { items: [], loading: false, error: null },
      ui: { theme: 'light', sidebarCollapsed: false, notifications: [] }
    };

    expect(selectors.getUserCount(emptyState)).toBe(0);
    expect(selectors.getAverageProductPrice(emptyState)).toBe(0);
    expect(selectors.getTotalRevenue(emptyState)).toBe(0);
    expect(selectors.getCurrentUser(emptyState)).toBeNull();
  });
});