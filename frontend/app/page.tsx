import AppNav from "@/components/AppNav";
import TopBar from "@/components/TopBar";
import Header from "@/components/Header";
import DocumentSidebar from "@/components/DocumentSidebar";
import DocumentViewer from "@/components/DocumentViewer";
import ChangesPanel from "@/components/ChangesPanel";
import { documents, history, pendingChanges, redlineMarkdown, searchHits } from "@/lib/mockData";

// The single app screen. Uses placeholder data until the API is wired up in Phase 3.
export default function Home() {
  const activeDocument = documents[0];

  return (
    <div className="flex h-screen overflow-hidden">
      <AppNav />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar documentTitle={activeDocument.title} />
        <div className="flex min-h-0 flex-1">
          <DocumentSidebar documents={documents} activeId={activeDocument.id} searchHits={searchHits} />
          <main className="flex min-w-0 flex-1 flex-col">
            <Header document={activeDocument} pendingCount={pendingChanges.length} />
            <div className="flex min-h-0 flex-1">
              <DocumentViewer markdown={redlineMarkdown} />
              <ChangesPanel pendingChanges={pendingChanges} history={history} />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
