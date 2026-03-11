"""Catalog indexing module for processing Shopify products."""

from .catalog_indexer import index_shopify_catalog, CatalogIndexer

__all__ = ["index_shopify_catalog", "CatalogIndexer"]
