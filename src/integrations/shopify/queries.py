GET_SHOP_INFO = """
query {
  shop {
    name
    myshopifyDomain
    primaryDomain {
      url
    }
  }
}
"""

GET_PRODUCTS = """
query GetProducts($first: Int!) {
  products(first: $first) {
    edges {
      node {
        id
        title
        handle
        status
        productType
        vendor
        totalInventory
      }
    }
  }
}
"""

GET_PRODUCT_DETAIL = """
query GetProduct($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    descriptionHtml
    status
    productType
    vendor
    tags
    totalInventory
    seo {
      title
      description
    }
    variants(first: 20) {
      edges {
        node {
          id
          title
          sku
          price
          compareAtPrice
          inventoryQuantity
        }
      }
    }
  }
}
"""

GET_RECENT_ORDERS = """
query GetRecentOrders($first: Int!) {
  orders(first: $first, sortKey: CREATED_AT, reverse: true) {
    edges {
      node {
        id
        name
        createdAt
        displayFinancialStatus
        displayFulfillmentStatus
        totalPriceSet {
          shopMoney {
            amount
            currencyCode
          }
        }
        lineItems(first: 20) {
          edges {
            node {
              title
              quantity
              originalUnitPriceSet {
                shopMoney {
                  amount
                  currencyCode
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

GET_PRODUCTS_FOR_AUDIT = """
query GetProductsForAudit($first: Int!) {
  products(first: $first) {
    edges {
      node {
        id
        title
        handle
        status
        productType
        vendor
        descriptionHtml
        totalInventory
        createdAt
        updatedAt
        seo {
          title
          description
        }
        variants(first: 20) {
          edges {
            node {
              id
              title
              sku
              price
              compareAtPrice
              inventoryQuantity
            }
          }
        }
      }
    }
  }
}
"""
