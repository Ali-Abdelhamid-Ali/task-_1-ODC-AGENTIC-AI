TRIGGERS_AND_INDEXES_SQL = """
SET search_path = public;

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = timezone('utc', now());
  RETURN NEW;
END;
$$;

-- Triggers (idempotent)
DROP TRIGGER IF EXISTS trg_customers_set_updatedat ON customers;
CREATE TRIGGER trg_customers_set_updatedat
BEFORE UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_vendors_set_updatedat ON vendors;
CREATE TRIGGER trg_vendors_set_updatedat
BEFORE UPDATE ON vendors
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_sites_set_updatedat ON sites;
CREATE TRIGGER trg_sites_set_updatedat
BEFORE UPDATE ON sites
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_locations_set_updatedat ON locations;
CREATE TRIGGER trg_locations_set_updatedat
BEFORE UPDATE ON locations
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_items_set_updatedat ON items;
CREATE TRIGGER trg_items_set_updatedat
BEFORE UPDATE ON items
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_assets_set_updatedat ON assets;
CREATE TRIGGER trg_assets_set_updatedat
BEFORE UPDATE ON assets
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_bills_set_updatedat ON bills;
CREATE TRIGGER trg_bills_set_updatedat
BEFORE UPDATE ON bills
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_purchase_orders_set_updatedat ON purchase_orders;
CREATE TRIGGER trg_purchase_orders_set_updatedat
BEFORE UPDATE ON purchase_orders
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_sales_orders_set_updatedat ON sales_orders;
CREATE TRIGGER trg_sales_orders_set_updatedat
BEFORE UPDATE ON sales_orders
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

-- Indexes
CREATE INDEX IF NOT EXISTS ix_locations_site_id            ON locations (site_id);
CREATE INDEX IF NOT EXISTS ix_locations_parent_location_id ON locations (parent_location_id);

CREATE INDEX IF NOT EXISTS ix_assets_site_id      ON assets (site_id);
CREATE INDEX IF NOT EXISTS ix_assets_location_id  ON assets (location_id);
CREATE INDEX IF NOT EXISTS ix_assets_vendor_id    ON assets (vendor_id);

CREATE INDEX IF NOT EXISTS ix_bills_vendor_id ON bills (vendor_id);

CREATE INDEX IF NOT EXISTS ix_purchase_orders_vendor_id ON purchase_orders (vendor_id);
CREATE INDEX IF NOT EXISTS ix_purchase_orders_site_id   ON purchase_orders (site_id);
CREATE INDEX IF NOT EXISTS ix_purchase_order_lines_po_id   ON purchase_order_lines (po_id);
CREATE INDEX IF NOT EXISTS ix_purchase_order_lines_item_id ON purchase_order_lines (item_id);

CREATE INDEX IF NOT EXISTS ix_sales_orders_customer_id ON sales_orders (customer_id);
CREATE INDEX IF NOT EXISTS ix_sales_orders_site_id     ON sales_orders (site_id);
CREATE INDEX IF NOT EXISTS ix_sales_order_lines_so_id   ON sales_order_lines (so_id);
CREATE INDEX IF NOT EXISTS ix_sales_order_lines_item_id ON sales_order_lines (item_id);

CREATE INDEX IF NOT EXISTS ix_asset_transactions_asset_id         ON asset_transactions (asset_id);
CREATE INDEX IF NOT EXISTS ix_asset_transactions_from_location_id  ON asset_transactions (from_location_id);
CREATE INDEX IF NOT EXISTS ix_asset_transactions_to_location_id    ON asset_transactions (to_location_id);
"""