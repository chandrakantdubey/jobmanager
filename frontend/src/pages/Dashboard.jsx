import { Link } from 'react-router-dom';

export default function Dashboard() {
    return (
        <div className="max-w-4xl mx-auto text-center py-20">
            <h1 className="text-4xl font-bold mb-6 text-gray-900">
                Welcome to your Job Application Manager
            </h1>
            <p className="text-xl text-gray-600 mb-12">
                Track resumes, find matching jobs, and manage your applications all in one place.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Link to="/resume" className="p-8 bg-white rounded-xl shadow border hover:shadow-lg transition-all group">
                    <div className="text-3xl mb-4">📄</div>
                    <h3 className="text-xl font-semibold mb-2 group-hover:text-blue-600">Upload Resume</h3>
                    <p className="text-gray-500">Parse your resume to find matching skills</p>
                </Link>
                <Link to="/search" className="p-8 bg-white rounded-xl shadow border hover:shadow-lg transition-all group">
                    <div className="text-3xl mb-4">🔍</div>
                    <h3 className="text-xl font-semibold mb-2 group-hover:text-blue-600">Find Jobs</h3>
                    <p className="text-gray-500">Search top platforms for matching roles</p>
                </Link>
                <Link to="/applications" className="p-8 bg-white rounded-xl shadow border hover:shadow-lg transition-all group">
                    <div className="text-3xl mb-4">📊</div>
                    <h3 className="text-xl font-semibold mb-2 group-hover:text-blue-600">Track Applications</h3>
                    <p className="text-gray-500">Keep status of all your applications</p>
                </Link>
            </div>
        </div>
    );
}
