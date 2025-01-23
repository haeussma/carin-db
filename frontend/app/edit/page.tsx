"use client";

import SpreadsheetUploader from '@/components/spreadsheet-uploader';
import DataTableCard from '@/components/data-table';
import AskCard from '@/components/ask-card';
import Header from '@/components/header';

export default function Page() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="p-8 bg-card text-card-foreground space-y-8">
        {/* Add Data (Spreadsheet Upload) */}
        <section id="add-data">
          <SpreadsheetUploader />
        </section>

        {/* Search/Data Table */}
        <section id="search">
          <DataTableCard />
        </section>

        {/* Ask */}
        <section id="ask">
          <AskCard />
        </section>
      </div>
    </div>
  );
}
