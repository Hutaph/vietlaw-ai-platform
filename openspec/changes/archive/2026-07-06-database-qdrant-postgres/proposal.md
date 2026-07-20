## Why

Hệ thống hiện tại phụ thuộc vào file JSON local và FAISS lưu trên ổ cứng, khiến việc cập nhật dữ liệu, quản lý embedding, reindex và scale-up trở nên khó khăn. Việc chuyển sang Qdrant cho vector storage và PostgreSQL cho metadata/document persistence sẽ giúp hệ thống có dữ liệu tập trung, dễ cập nhật, dễ vận hành hơn và phù hợp cho các feature tiếp theo như incremental indexing, versioning, filtering và quản trị nội dung pháp luật.

## What Changes

- Thay thế phần lưu trữ vector hiện tại từ FAISS local sang Qdrant, với collection riêng cho các clause/chunk pháp luật.
- Thêm PostgreSQL làm nguồn dữ liệu chính cho metadata pháp luật, thông tin điều khoản, trạng thái indexing và các thuộc tính lọc như category, law_id, version.
- Tách luồng ingestion dữ liệu thành một pipeline rõ ràng: ingest JSON → normalize → lưu PostgreSQL → tạo embedding → upsert vào Qdrant.
- Giữ nguyên contract API hiện tại cho chat endpoint để frontend không bị ảnh hưởng, nhưng thay đổi phần implement bên trong backend.
- Thêm cấu hình môi trường và Docker services cho Qdrant và PostgreSQL, đồng thời hỗ trợ khởi tạo schema/migration ban đầu.
- Mở đường cho các feature tương lai như reindex incremental, delete/update document, audit trail và quản lý dữ liệu theo phiên bản.

## Capabilities

### New Capabilities
- document-ingestion: ingest và normalize dữ liệu pháp luật từ JSON vào hệ thống có cấu trúc, bao gồm metadata và clause-level records.
- vector-storage: lưu trữ embedding và metadata vector trong Qdrant với hỗ trợ filter và upsert hiệu quả.
- retrieval-persistence: cung cấp truy xuất pháp luật dựa trên dữ liệu được lưu trong PostgreSQL + Qdrant với trải nghiệm tương tự pipeline hiện tại.

### Modified Capabilities
- legal-retrieval: thay đổi cách hệ thống lưu trữ và truy xuất tài liệu pháp luật từ local-file/FAISS sang DB-backed vector + relational metadata.

## Impact

- Backend: thay đổi đáng kể ở các module liên quan đến vectorstore, knowledge base, pipeline và cấu hình môi trường.
- Data layer: cần thêm Qdrant và PostgreSQL vào stack vận hành, cùng các migration/schema và scripts seed dữ liệu.
- DevOps: docker-compose và biến môi trường cần cập nhật để hỗ trợ cả hai service mới.
- Frontend: không bắt bu đổi API public, nhưng có thể cần điều chỉnh UI nếu muốn hiển thị trạng thái indexing hoặc source metadata rõ hơn.
- Dependencies: cần thêm thư viện Python cho kết nối PostgreSQL và Qdrant, đồng thời thay đổi cách khởi tạo index ban đầu.
