import { Fragment } from 'react';
import { NextPage } from 'next';

const HomePage: NextPage = () => {
  return (
    <Fragment>
      <div className="flex flex-col items-center justify-center min-h-screen py-2">
        <main className="flex flex-col items-center justify-center w-full flex-1 px-20 text-center">
          <h1 className="text-6xl font-bold">
            Welcome to <a className="text-blue-600" href="https://netrasystems.ai">Netra!</a>
          </h1>

          <p className="mt-3 text-2xl">
            Get started by logging in.
          </p>
        </main>
      </div>
    </Fragment>
  );
};

export default HomePage;
