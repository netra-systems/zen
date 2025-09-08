/**
 * Store Actions Test Suite
 * 37 comprehensive tests for store action functions and reducers
 */

// Action types
const ActionTypes = {
  // User actions
  FETCH_USERS_REQUEST: 'FETCH_USERS_REQUEST',
  FETCH_USERS_SUCCESS: 'FETCH_USERS_SUCCESS',
  FETCH_USERS_FAILURE: 'FETCH_USERS_FAILURE',
  SET_CURRENT_USER: 'SET_CURRENT_USER',
  UPDATE_USER: 'UPDATE_USER',
  DELETE_USER: 'DELETE_USER',
  
  // Product actions
  FETCH_PRODUCTS_REQUEST: 'FETCH_PRODUCTS_REQUEST',
  FETCH_PRODUCTS_SUCCESS: 'FETCH_PRODUCTS_SUCCESS',
  FETCH_PRODUCTS_FAILURE: 'FETCH_PRODUCTS_FAILURE',
  ADD_PRODUCT: 'ADD_PRODUCT',
  UPDATE_PRODUCT: 'UPDATE_PRODUCT',
  DELETE_PRODUCT: 'DELETE_PRODUCT',
  SET_PRODUCT_FILTERS: 'SET_PRODUCT_FILTERS',
  CLEAR_PRODUCT_FILTERS: 'CLEAR_PRODUCT_FILTERS',
  
  // Order actions
  FETCH_ORDERS_REQUEST: 'FETCH_ORDERS_REQUEST',
  FETCH_ORDERS_SUCCESS: 'FETCH_ORDERS_SUCCESS',
  FETCH_ORDERS_FAILURE: 'FETCH_ORDERS_FAILURE',
  CREATE_ORDER: 'CREATE_ORDER',
  UPDATE_ORDER_STATUS: 'UPDATE_ORDER_STATUS',
  CANCEL_ORDER: 'CANCEL_ORDER',
  
  // UI actions
  SET_THEME: 'SET_THEME',
  TOGGLE_SIDEBAR: 'SET_SIDEBAR_COLLAPSED',
  ADD_NOTIFICATION: 'ADD_NOTIFICATION',
  REMOVE_NOTIFICATION: 'REMOVE_NOTIFICATION',
  CLEAR_NOTIFICATIONS: 'CLEAR_NOTIFICATIONS'
} as const;

// Interfaces
interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user' | 'guest';
  isActive: boolean;
}

interface Product {
  id: string;
  name: string;
  price: number;
  category: string;
  inStock: boolean;
}

interface Order {
  id: string;
  userId: string;
  products: { productId: string; quantity: number; price: number }[];
  status: 'pending' | 'processing' | 'shipped' | 'delivered' | 'cancelled';
  total: number;
}

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  timestamp: number;
}

// Action creators
const actionCreators = {
  // User action creators
  fetchUsersRequest: () => ({ type: ActionTypes.FETCH_USERS_REQUEST }),
  fetchUsersSuccess: (users: User[]) => ({ type: ActionTypes.FETCH_USERS_SUCCESS, payload: users }),
  fetchUsersFailure: (error: string) => ({ type: ActionTypes.FETCH_USERS_FAILURE, payload: error }),
  setCurrentUser: (userId: string | null) => ({ type: ActionTypes.SET_CURRENT_USER, payload: userId }),
  updateUser: (user: User) => ({ type: ActionTypes.UPDATE_USER, payload: user }),
  deleteUser: (userId: string) => ({ type: ActionTypes.DELETE_USER, payload: userId }),

  // Product action creators
  fetchProductsRequest: () => ({ type: ActionTypes.FETCH_PRODUCTS_REQUEST }),
  fetchProductsSuccess: (products: Product[]) => ({ type: ActionTypes.FETCH_PRODUCTS_SUCCESS, payload: products }),
  fetchProductsFailure: (error: string) => ({ type: ActionTypes.FETCH_PRODUCTS_FAILURE, payload: error }),
  addProduct: (product: Product) => ({ type: ActionTypes.ADD_PRODUCT, payload: product }),
  updateProduct: (product: Product) => ({ type: ActionTypes.UPDATE_PRODUCT, payload: product }),
  deleteProduct: (productId: string) => ({ type: ActionTypes.DELETE_PRODUCT, payload: productId }),
  setProductFilters: (filters: any) => ({ type: ActionTypes.SET_PRODUCT_FILTERS, payload: filters }),
  clearProductFilters: () => ({ type: ActionTypes.CLEAR_PRODUCT_FILTERS }),

  // Order action creators
  fetchOrdersRequest: () => ({ type: ActionTypes.FETCH_ORDERS_REQUEST }),
  fetchOrdersSuccess: (orders: Order[]) => ({ type: ActionTypes.FETCH_ORDERS_SUCCESS, payload: orders }),
  fetchOrdersFailure: (error: string) => ({ type: ActionTypes.FETCH_ORDERS_FAILURE, payload: error }),
  createOrder: (order: Order) => ({ type: ActionTypes.CREATE_ORDER, payload: order }),
  updateOrderStatus: (orderId: string, status: Order['status']) => ({
    type: ActionTypes.UPDATE_ORDER_STATUS,
    payload: { orderId, status }
  }),
  cancelOrder: (orderId: string) => ({ type: ActionTypes.CANCEL_ORDER, payload: orderId }),

  // UI action creators
  setTheme: (theme: 'light' | 'dark') => ({ type: ActionTypes.SET_THEME, payload: theme }),
  toggleSidebar: () => ({ type: ActionTypes.TOGGLE_SIDEBAR }),
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => ({
    type: ActionTypes.ADD_NOTIFICATION,
    payload: {
      ...notification,
      id: Math.random().toString(36),
      timestamp: Date.now()
    }
  }),
  removeNotification: (notificationId: string) => ({
    type: ActionTypes.REMOVE_NOTIFICATION,
    payload: notificationId
  }),
  clearNotifications: () => ({ type: ActionTypes.CLEAR_NOTIFICATIONS })
};

// Initial states
const initialUserState = {
  items: [] as User[],
  loading: false,
  error: null as string | null,
  currentUserId: null as string | null
};

const initialProductState = {
  items: [] as Product[],
  loading: false,
  error: null as string | null,
  filters: {
    category: null as string | null,
    priceRange: null as { min: number; max: number } | null,
    inStockOnly: false
  }
};

const initialOrderState = {
  items: [] as Order[],
  loading: false,
  error: null as string | null
};

const initialUIState = {
  theme: 'light' as 'light' | 'dark',
  sidebarCollapsed: false,
  notifications: [] as Notification[]
};

// Reducers
const userReducer = (state = initialUserState, action: any) => {
  switch (action.type) {
    case ActionTypes.FETCH_USERS_REQUEST:
      return { ...state, loading: true, error: null };
    
    case ActionTypes.FETCH_USERS_SUCCESS:
      return { ...state, loading: false, items: action.payload, error: null };
    
    case ActionTypes.FETCH_USERS_FAILURE:
      return { ...state, loading: false, error: action.payload };
    
    case ActionTypes.SET_CURRENT_USER:
      return { ...state, currentUserId: action.payload };
    
    case ActionTypes.UPDATE_USER:
      return {
        ...state,
        items: state.items.map(user =>
          user.id === action.payload.id ? action.payload : user
        )
      };
    
    case ActionTypes.DELETE_USER:
      return {
        ...state,
        items: state.items.filter(user => user.id !== action.payload),
        currentUserId: state.currentUserId === action.payload ? null : state.currentUserId
      };
    
    default:
      return state;
  }
};

const productReducer = (state = initialProductState, action: any) => {
  switch (action.type) {
    case ActionTypes.FETCH_PRODUCTS_REQUEST:
      return { ...state, loading: true, error: null };
    
    case ActionTypes.FETCH_PRODUCTS_SUCCESS:
      return { ...state, loading: false, items: action.payload, error: null };
    
    case ActionTypes.FETCH_PRODUCTS_FAILURE:
      return { ...state, loading: false, error: action.payload };
    
    case ActionTypes.ADD_PRODUCT:
      return { ...state, items: [...state.items, action.payload] };
    
    case ActionTypes.UPDATE_PRODUCT:
      return {
        ...state,
        items: state.items.map(product =>
          product.id === action.payload.id ? action.payload : product
        )
      };
    
    case ActionTypes.DELETE_PRODUCT:
      return {
        ...state,
        items: state.items.filter(product => product.id !== action.payload)
      };
    
    case ActionTypes.SET_PRODUCT_FILTERS:
      return { ...state, filters: { ...state.filters, ...action.payload } };
    
    case ActionTypes.CLEAR_PRODUCT_FILTERS:
      return {
        ...state,
        filters: { category: null, priceRange: null, inStockOnly: false }
      };
    
    default:
      return state;
  }
};

const orderReducer = (state = initialOrderState, action: any) => {
  switch (action.type) {
    case ActionTypes.FETCH_ORDERS_REQUEST:
      return { ...state, loading: true, error: null };
    
    case ActionTypes.FETCH_ORDERS_SUCCESS:
      return { ...state, loading: false, items: action.payload, error: null };
    
    case ActionTypes.FETCH_ORDERS_FAILURE:
      return { ...state, loading: false, error: action.payload };
    
    case ActionTypes.CREATE_ORDER:
      return { ...state, items: [...state.items, action.payload] };
    
    case ActionTypes.UPDATE_ORDER_STATUS:
      return {
        ...state,
        items: state.items.map(order =>
          order.id === action.payload.orderId
            ? { ...order, status: action.payload.status }
            : order
        )
      };
    
    case ActionTypes.CANCEL_ORDER:
      return {
        ...state,
        items: state.items.map(order =>
          order.id === action.payload ? { ...order, status: 'cancelled' as const } : order
        )
      };
    
    default:
      return state;
  }
};

const uiReducer = (state = initialUIState, action: any) => {
  switch (action.type) {
    case ActionTypes.SET_THEME:
      return { ...state, theme: action.payload };
    
    case ActionTypes.TOGGLE_SIDEBAR:
      return { ...state, sidebarCollapsed: !state.sidebarCollapsed };
    
    case ActionTypes.ADD_NOTIFICATION:
      return { ...state, notifications: [...state.notifications, action.payload] };
    
    case ActionTypes.REMOVE_NOTIFICATION:
      return {
        ...state,
        notifications: state.notifications.filter(n => n.id !== action.payload)
      };
    
    case ActionTypes.CLEAR_NOTIFICATIONS:
      return { ...state, notifications: [] };
    
    default:
      return state;
  }
};

describe('User Action Creators', () => {
  test('should create fetch users request action', () => {
    const action = actionCreators.fetchUsersRequest();
    expect(action).toEqual({ type: ActionTypes.FETCH_USERS_REQUEST });
  });

  test('should create fetch users success action', () => {
    const users: User[] = [
      { id: '1', name: 'John', email: 'john@test.com', role: 'user', isActive: true }
    ];
    const action = actionCreators.fetchUsersSuccess(users);
    expect(action).toEqual({ type: ActionTypes.FETCH_USERS_SUCCESS, payload: users });
  });

  test('should create fetch users failure action', () => {
    const error = 'Failed to fetch users';
    const action = actionCreators.fetchUsersFailure(error);
    expect(action).toEqual({ type: ActionTypes.FETCH_USERS_FAILURE, payload: error });
  });

  test('should create set current user action', () => {
    const userId = 'user123';
    const action = actionCreators.setCurrentUser(userId);
    expect(action).toEqual({ type: ActionTypes.SET_CURRENT_USER, payload: userId });
  });

  test('should create update user action', () => {
    const user: User = { id: '1', name: 'John', email: 'john@test.com', role: 'user', isActive: true };
    const action = actionCreators.updateUser(user);
    expect(action).toEqual({ type: ActionTypes.UPDATE_USER, payload: user });
  });

  test('should create delete user action', () => {
    const userId = 'user123';
    const action = actionCreators.deleteUser(userId);
    expect(action).toEqual({ type: ActionTypes.DELETE_USER, payload: userId });
  });
});

describe('Product Action Creators', () => {
  test('should create fetch products request action', () => {
    const action = actionCreators.fetchProductsRequest();
    expect(action).toEqual({ type: ActionTypes.FETCH_PRODUCTS_REQUEST });
  });

  test('should create fetch products success action', () => {
    const products: Product[] = [
      { id: '1', name: 'Laptop', price: 1000, category: 'Electronics', inStock: true }
    ];
    const action = actionCreators.fetchProductsSuccess(products);
    expect(action).toEqual({ type: ActionTypes.FETCH_PRODUCTS_SUCCESS, payload: products });
  });

  test('should create add product action', () => {
    const product: Product = { id: '1', name: 'Laptop', price: 1000, category: 'Electronics', inStock: true };
    const action = actionCreators.addProduct(product);
    expect(action).toEqual({ type: ActionTypes.ADD_PRODUCT, payload: product });
  });

  test('should create set product filters action', () => {
    const filters = { category: 'Electronics', inStockOnly: true };
    const action = actionCreators.setProductFilters(filters);
    expect(action).toEqual({ type: ActionTypes.SET_PRODUCT_FILTERS, payload: filters });
  });

  test('should create clear product filters action', () => {
    const action = actionCreators.clearProductFilters();
    expect(action).toEqual({ type: ActionTypes.CLEAR_PRODUCT_FILTERS });
  });
});

describe('Order Action Creators', () => {
  test('should create order actions', () => {
    const order: Order = {
      id: '1',
      userId: 'user1',
      products: [{ productId: 'p1', quantity: 1, price: 100 }],
      status: 'pending',
      total: 100
    };

    expect(actionCreators.createOrder(order)).toEqual({
      type: ActionTypes.CREATE_ORDER,
      payload: order
    });
  });

  test('should create update order status action', () => {
    const action = actionCreators.updateOrderStatus('order1', 'shipped');
    expect(action).toEqual({
      type: ActionTypes.UPDATE_ORDER_STATUS,
      payload: { orderId: 'order1', status: 'shipped' }
    });
  });

  test('should create cancel order action', () => {
    const action = actionCreators.cancelOrder('order1');
    expect(action).toEqual({ type: ActionTypes.CANCEL_ORDER, payload: 'order1' });
  });
});

describe('UI Action Creators', () => {
  test('should create set theme action', () => {
    const action = actionCreators.setTheme('dark');
    expect(action).toEqual({ type: ActionTypes.SET_THEME, payload: 'dark' });
  });

  test('should create toggle sidebar action', () => {
    const action = actionCreators.toggleSidebar();
    expect(action).toEqual({ type: ActionTypes.TOGGLE_SIDEBAR });
  });

  test('should create add notification action with generated id and timestamp', () => {
    const notification = { type: 'success' as const, message: 'Success!' };
    const action = actionCreators.addNotification(notification);
    
    expect(action.type).toBe(ActionTypes.ADD_NOTIFICATION);
    expect(action.payload.type).toBe('success');
    expect(action.payload.message).toBe('Success!');
    expect(action.payload.id).toBeDefined();
    expect(action.payload.timestamp).toBeDefined();
  });
});

describe('User Reducer', () => {
  test('should handle fetch users request', () => {
    const action = actionCreators.fetchUsersRequest();
    const newState = userReducer(initialUserState, action);
    
    expect(newState.loading).toBe(true);
    expect(newState.error).toBeNull();
  });

  test('should handle fetch users success', () => {
    const users: User[] = [
      { id: '1', name: 'John', email: 'john@test.com', role: 'user', isActive: true }
    ];
    const action = actionCreators.fetchUsersSuccess(users);
    const newState = userReducer(initialUserState, action);
    
    expect(newState.loading).toBe(false);
    expect(newState.items).toEqual(users);
    expect(newState.error).toBeNull();
  });

  test('should handle fetch users failure', () => {
    const error = 'Network error';
    const action = actionCreators.fetchUsersFailure(error);
    const newState = userReducer(initialUserState, action);
    
    expect(newState.loading).toBe(false);
    expect(newState.error).toBe(error);
  });

  test('should handle set current user', () => {
    const userId = 'user123';
    const action = actionCreators.setCurrentUser(userId);
    const newState = userReducer(initialUserState, action);
    
    expect(newState.currentUserId).toBe(userId);
  });

  test('should handle update user', () => {
    const initialState = {
      ...initialUserState,
      items: [
        { id: '1', name: 'John', email: 'john@test.com', role: 'user' as const, isActive: true },
        { id: '2', name: 'Jane', email: 'jane@test.com', role: 'admin' as const, isActive: true }
      ]
    };

    const updatedUser: User = { id: '1', name: 'John Updated', email: 'john@test.com', role: 'admin', isActive: false };
    const action = actionCreators.updateUser(updatedUser);
    const newState = userReducer(initialState, action);
    
    expect(newState.items[0]).toEqual(updatedUser);
    expect(newState.items[1]).toEqual(initialState.items[1]);
  });

  test('should handle delete user', () => {
    const initialState = {
      ...initialUserState,
      items: [
        { id: '1', name: 'John', email: 'john@test.com', role: 'user' as const, isActive: true },
        { id: '2', name: 'Jane', email: 'jane@test.com', role: 'admin' as const, isActive: true }
      ],
      currentUserId: '1'
    };

    const action = actionCreators.deleteUser('1');
    const newState = userReducer(initialState, action);
    
    expect(newState.items).toHaveLength(1);
    expect(newState.items[0].id).toBe('2');
    expect(newState.currentUserId).toBeNull();
  });
});

describe('Product Reducer', () => {
  test('should handle add product', () => {
    const product: Product = { id: '1', name: 'Laptop', price: 1000, category: 'Electronics', inStock: true };
    const action = actionCreators.addProduct(product);
    const newState = productReducer(initialProductState, action);
    
    expect(newState.items).toHaveLength(1);
    expect(newState.items[0]).toEqual(product);
  });

  test('should handle update product', () => {
    const initialState = {
      ...initialProductState,
      items: [
        { id: '1', name: 'Laptop', price: 1000, category: 'Electronics', inStock: true },
        { id: '2', name: 'Phone', price: 500, category: 'Electronics', inStock: false }
      ]
    };

    const updatedProduct: Product = { id: '1', name: 'Gaming Laptop', price: 1500, category: 'Electronics', inStock: true };
    const action = actionCreators.updateProduct(updatedProduct);
    const newState = productReducer(initialState, action);
    
    expect(newState.items[0]).toEqual(updatedProduct);
    expect(newState.items[1]).toEqual(initialState.items[1]);
  });

  test('should handle delete product', () => {
    const initialState = {
      ...initialProductState,
      items: [
        { id: '1', name: 'Laptop', price: 1000, category: 'Electronics', inStock: true },
        { id: '2', name: 'Phone', price: 500, category: 'Electronics', inStock: false }
      ]
    };

    const action = actionCreators.deleteProduct('1');
    const newState = productReducer(initialState, action);
    
    expect(newState.items).toHaveLength(1);
    expect(newState.items[0].id).toBe('2');
  });

  test('should handle set product filters', () => {
    const filters = { category: 'Electronics', inStockOnly: true };
    const action = actionCreators.setProductFilters(filters);
    const newState = productReducer(initialProductState, action);
    
    expect(newState.filters.category).toBe('Electronics');
    expect(newState.filters.inStockOnly).toBe(true);
  });

  test('should handle clear product filters', () => {
    const initialState = {
      ...initialProductState,
      filters: { category: 'Electronics', priceRange: { min: 0, max: 1000 }, inStockOnly: true }
    };

    const action = actionCreators.clearProductFilters();
    const newState = productReducer(initialState, action);
    
    expect(newState.filters).toEqual({
      category: null,
      priceRange: null,
      inStockOnly: false
    });
  });
});

describe('Order Reducer', () => {
  test('should handle create order', () => {
    const order: Order = {
      id: '1',
      userId: 'user1',
      products: [{ productId: 'p1', quantity: 1, price: 100 }],
      status: 'pending',
      total: 100
    };

    const action = actionCreators.createOrder(order);
    const newState = orderReducer(initialOrderState, action);
    
    expect(newState.items).toHaveLength(1);
    expect(newState.items[0]).toEqual(order);
  });

  test('should handle update order status', () => {
    const initialState = {
      ...initialOrderState,
      items: [
        {
          id: '1',
          userId: 'user1',
          products: [{ productId: 'p1', quantity: 1, price: 100 }],
          status: 'pending' as const,
          total: 100
        }
      ]
    };

    const action = actionCreators.updateOrderStatus('1', 'shipped');
    const newState = orderReducer(initialState, action);
    
    expect(newState.items[0].status).toBe('shipped');
  });

  test('should handle cancel order', () => {
    const initialState = {
      ...initialOrderState,
      items: [
        {
          id: '1',
          userId: 'user1',
          products: [{ productId: 'p1', quantity: 1, price: 100 }],
          status: 'pending' as const,
          total: 100
        }
      ]
    };

    const action = actionCreators.cancelOrder('1');
    const newState = orderReducer(initialState, action);
    
    expect(newState.items[0].status).toBe('cancelled');
  });
});

describe('UI Reducer', () => {
  test('should handle set theme', () => {
    const action = actionCreators.setTheme('dark');
    const newState = uiReducer(initialUIState, action);
    
    expect(newState.theme).toBe('dark');
  });

  test('should handle toggle sidebar', () => {
    const action = actionCreators.toggleSidebar();
    const newState = uiReducer(initialUIState, action);
    
    expect(newState.sidebarCollapsed).toBe(true);
    
    const secondState = uiReducer(newState, action);
    expect(secondState.sidebarCollapsed).toBe(false);
  });

  test('should handle add notification', () => {
    const notification = { type: 'success' as const, message: 'Test message' };
    const action = actionCreators.addNotification(notification);
    const newState = uiReducer(initialUIState, action);
    
    expect(newState.notifications).toHaveLength(1);
    expect(newState.notifications[0].message).toBe('Test message');
    expect(newState.notifications[0].type).toBe('success');
  });

  test('should handle remove notification', () => {
    const initialState = {
      ...initialUIState,
      notifications: [
        { id: '1', type: 'success' as const, message: 'Message 1', timestamp: Date.now() },
        { id: '2', type: 'error' as const, message: 'Message 2', timestamp: Date.now() }
      ]
    };

    const action = actionCreators.removeNotification('1');
    const newState = uiReducer(initialState, action);
    
    expect(newState.notifications).toHaveLength(1);
    expect(newState.notifications[0].id).toBe('2');
  });

  test('should handle clear notifications', () => {
    const initialState = {
      ...initialUIState,
      notifications: [
        { id: '1', type: 'success' as const, message: 'Message 1', timestamp: Date.now() },
        { id: '2', type: 'error' as const, message: 'Message 2', timestamp: Date.now() }
      ]
    };

    const action = actionCreators.clearNotifications();
    const newState = uiReducer(initialState, action);
    
    expect(newState.notifications).toHaveLength(0);
  });
});

describe('Complex Action Scenarios', () => {
  test('should handle multiple actions in sequence', () => {
    let state = initialUserState;
    
    // Start loading
    state = userReducer(state, actionCreators.fetchUsersRequest());
    expect(state.loading).toBe(true);
    
    // Load users successfully
    const users: User[] = [
      { id: '1', name: 'John', email: 'john@test.com', role: 'user', isActive: true },
      { id: '2', name: 'Jane', email: 'jane@test.com', role: 'admin', isActive: true }
    ];
    state = userReducer(state, actionCreators.fetchUsersSuccess(users));
    expect(state.loading).toBe(false);
    expect(state.items).toHaveLength(2);
    
    // Set current user
    state = userReducer(state, actionCreators.setCurrentUser('1'));
    expect(state.currentUserId).toBe('1');
    
    // Update a user
    const updatedUser: User = { ...users[0], name: 'John Updated' };
    state = userReducer(state, actionCreators.updateUser(updatedUser));
    expect(state.items[0].name).toBe('John Updated');
    
    // Delete a user
    state = userReducer(state, actionCreators.deleteUser('2'));
    expect(state.items).toHaveLength(1);
    expect(state.items[0].id).toBe('1');
  });

  test('should handle state consistency across reducers', () => {
    const userId = 'user123';
    const orderId = 'order123';
    
    // Create user
    let userState = initialUserState;
    const user: User = { id: userId, name: 'John', email: 'john@test.com', role: 'user', isActive: true };
    userState = userReducer(userState, actionCreators.fetchUsersSuccess([user]));
    userState = userReducer(userState, actionCreators.setCurrentUser(userId));
    
    // Create order for user
    let orderState = initialOrderState;
    const order: Order = {
      id: orderId,
      userId: userId,
      products: [{ productId: 'p1', quantity: 1, price: 100 }],
      status: 'pending',
      total: 100
    };
    orderState = orderReducer(orderState, actionCreators.createOrder(order));
    
    expect(userState.currentUserId).toBe(userId);
    expect(orderState.items[0].userId).toBe(userId);
  });
});

describe('Error Handling', () => {
  test('should handle unknown action types gracefully', () => {
    const unknownAction = { type: 'UNKNOWN_ACTION', payload: 'test' };
    
    expect(userReducer(initialUserState, unknownAction)).toEqual(initialUserState);
    expect(productReducer(initialProductState, unknownAction)).toEqual(initialProductState);
    expect(orderReducer(initialOrderState, unknownAction)).toEqual(initialOrderState);
    expect(uiReducer(initialUIState, unknownAction)).toEqual(initialUIState);
  });

  test('should handle undefined state gracefully', () => {
    const action = actionCreators.fetchUsersRequest();
    
    expect(userReducer(undefined, action)).toEqual({
      ...initialUserState,
      loading: true,
      error: null
    });
  });
});