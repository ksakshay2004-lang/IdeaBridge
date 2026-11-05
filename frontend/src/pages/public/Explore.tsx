import ExploreView from "../../components/ExploreView";

export default function Explore() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-bold">Explore ideas</h1>
      <p className="mb-6 mt-1 text-slate-600">Public ideas from creators around the world. Sign in to see restricted listings and contact creators.</p>
      <ExploreView detailBase="/ideas" />
    </div>
  );
}
