
import db from "./db.js";

/**
 * ✅ GET CUSTOMER DATA
 */
export const getCustomerData = async (shop, customerId) => {
  try {
    const customer = await db.collection("customers").findOne({
      shop,
      customerId,
    });

    const orders = await db
      .collection("orders")
      .find({ shop, customerId })
      .toArray();

    const aiResults = await db
      .collection("ai_results")
      .find({ shop, customerId })
      .toArray();

    return {
      customer,
      orders,
      aiResults,
    };
  } catch (err) {
    console.error("Error fetching customer data:", err);
    throw err;
  }
};

/**
 * ✅ DELETE CUSTOMER DATA
 */
export const deleteCustomerData = async (shop, customerId) => {
  try {
    await db.collection("customers").deleteMany({ shop, customerId });

    await db.collection("orders").deleteMany({ shop, customerId });

    await db.collection("ai_results").deleteMany({ shop, customerId });

    // 🔥 DELETE AI FILES / CACHE 
    await deleteAIFilesForCustomer(shop, customerId);

    console.log(`Customer ${customerId} fully deleted`);
  } catch (err) {
    console.error("Error deleting customer:", err);
    throw err;
  }
};

/**
 * 
 */
export const deleteShopData = async (shop) => {
  try {
    await db.collection("customers").deleteMany({ shop });
    await db.collection("orders").deleteMany({ shop });
    await db.collection("ai_results").deleteMany({ shop });

    // 
    await deleteAIFilesForShop(shop);

    console.log(`Shop ${shop} fully wiped`);
  } catch (err) {
    console.error("Error deleting shop:", err);
    throw err;
  }
};

/**
 * 
 */
const deleteAIFilesForCustomer = async (shop, customerId) => {
  // Example:
  // delete generated outfits, embeddings, images

  console.log(`Deleting AI data for customer ${customerId}`);
};

const deleteAIFilesForShop = async (shop) => {
  console.log(`Deleting ALL AI data for shop ${shop}`);
};
