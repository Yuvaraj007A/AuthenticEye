import React from 'react';
import Hero from '../components/Hero';
import Features from '../components/Features';
import Industries from '../components/Industries';
import Metrics from '../components/Metrics';
import FAQ from '../components/FAQ';

const Home = () => {
  return (
    <>
      <Hero />
      <Features />
      <Metrics />
      <Industries />
      <FAQ />
    </>
  );
};

export default Home;
